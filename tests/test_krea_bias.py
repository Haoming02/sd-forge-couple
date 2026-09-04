import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import torch

from lib_couple import krea_bias as B


def halves(h=2, w=4):
    """Line 0 = left half, line 1 = right half. (2, h, w)"""
    spatial = torch.zeros(2, h, w)
    spatial[0, :, : w // 2] = 1.0
    spatial[1, :, w // 2 :] = 1.0
    return spatial


def with_global(h=2, w=4, bg=0.5):
    """Line 0 = full-frame global at weight bg, lines 1-2 = halves. (3, h, w)"""
    return torch.cat([torch.full((1, h, w), bg), halves(h, w)], dim=0)


class FindGlobals(unittest.TestCase):
    def test_full_frame_is_global(self):
        self.assertEqual(B.find_globals(with_global()), [True, False, False])

    def test_no_global(self):
        self.assertEqual(B.find_globals(halves()), [False, False])

    def test_almost_full_is_not_global(self):
        m = torch.ones(1, 4, 4)
        m[0, 0, 0] = 0.0
        self.assertEqual(B.find_globals(m), [False])

    def test_last_line_global(self):
        spatial = torch.cat([halves(), torch.full((1, 2, 4), 0.5)], dim=0)
        self.assertEqual(B.find_globals(spatial), [False, False, True])


class ResizeMasks(unittest.TestCase):
    def test_shape_and_values(self):
        r = B.resize_masks(halves(8, 8), 2, 4)
        self.assertEqual(tuple(r.shape), (2, 8))
        self.assertEqual(r[0, 0].item(), 1.0)
        self.assertEqual(r[0, 3].item(), 0.0)
        self.assertTrue((r >= 0).all())

    def test_weight_above_one_survives(self):
        r = B.resize_masks(torch.full((1, 4, 4), 2.0), 2, 2)
        self.assertAlmostEqual(r.max().item(), 2.0, places=5)


class LogWeight(unittest.TestCase):
    def test_values(self):
        out = B.log_weight(torch.tensor([1.0, 0.5, 0.0, 2.0]))
        self.assertEqual(out[0].item(), 0.0)
        self.assertAlmostEqual(out[1].item(), math.log(0.5), places=5)
        self.assertEqual(out[2].item(), B.NEG)
        self.assertAlmostEqual(out[3].item(), math.log(2.0), places=5)


class BuildBias(unittest.TestCase):
    def setUp(self):
        self.h, self.w = 2, 4
        self.N = self.h * self.w
        self.masks = B.resize_masks(with_global(self.h, self.w, 0.5), self.h, self.w)  # (3, 8)
        self.seg_lens = [3, 2, 2]  # global, left, right
        self.is_global = [True, False, False]
        self.T = sum(self.seg_lens)

    def bias(self, gate=False, masks=None, seg_lens=None, is_global=None):
        return B.build_bias(
            seg_lens or self.seg_lens,
            self.masks if masks is None else masks,
            is_global or self.is_global,
            gate,
        )

    def test_shape_and_no_blocked_rows(self):
        for gate in (False, True):
            b = self.bias(gate)
            self.assertEqual(tuple(b.shape), (self.T + self.N, self.T + self.N))
            self.assertTrue((b.max(dim=1).values > B.NEG).all(), "every query row needs one readable key")
            self.assertTrue((torch.diagonal(b) == 0).all(), "a token can always read itself")

    def test_text_block_diagonal_with_global_readable(self):
        b = self.bias()
        # left text (rows 3..4) reads itself and the global (cols 0..4), not right text (cols 5..6)
        self.assertTrue((b[3:5, 0:5] == 0).all())
        self.assertTrue((b[3:5, 5:7] == B.NEG).all())
        # global text reads only itself among text
        self.assertTrue((b[0:3, 0:3] == 0).all())
        self.assertTrue((b[0:3, 3:7] == B.NEG).all())

    def test_image_reads_own_line_and_global(self):
        b = self.bias()
        img0 = self.T + 0  # left-half token
        img7 = self.T + 7  # right-half token
        self.assertTrue((b[img0, 3:5] == 0).all())
        self.assertTrue((b[img0, 5:7] == B.NEG).all())
        self.assertTrue((b[img7, 5:7] == 0).all())
        self.assertTrue((b[img7, 3:5] == B.NEG).all())
        # global weight comes from the mask value
        self.assertAlmostEqual(b[img0, 0].item(), math.log(0.5), places=5)

    def test_text_reads_own_image(self):
        b = self.bias()
        self.assertTrue((b[3:5, self.T : self.T + 2] == 0).all())  # left text -> left tokens
        self.assertTrue((b[3:5, self.T + 2 : self.T + 4] == B.NEG).all())  # left text -> right tokens
        self.assertTrue((b[0:3, self.T :] == 0).all())  # global text -> all image

    def test_uncovered_token_reads_everything(self):
        masks = self.masks.clone()
        masks[1:, 7] = 0.0  # last token covered by no regional line (global still covers it)
        b = self.bias(True, masks=masks)
        self.assertTrue((b[self.T + 7, : self.T] == 0).all())
        self.assertTrue((b[self.T + 7, self.T :] == 0).all())
        self.assertTrue((b[self.T :, self.T + 7] == 0).all())

    def test_image_gating_only_when_requested(self):
        ungated = self.bias(False)
        gated = self.bias(True)
        img = slice(self.T, self.T + self.N)
        self.assertTrue((ungated[img, img] == 0).all())
        self.assertEqual(gated[self.T + 0, self.T + 1].item(), 0.0)  # same line
        self.assertEqual(gated[self.T + 0, self.T + 7].item(), B.NEG)  # different lines

    def test_global_never_counts_as_shared(self):
        # the global line covers every token; without this rule gating would never block anything
        gated = self.bias(True)
        self.assertEqual(gated[self.T + 0, self.T + 7].item(), B.NEG)

    def test_no_global(self):
        masks = B.resize_masks(halves(self.h, self.w), self.h, self.w)
        b = B.build_bias([2, 2], masks, [False, False], False)
        self.assertEqual(tuple(b.shape), (4 + self.N, 4 + self.N))
        self.assertTrue((b[0:2, 2:4] == B.NEG).all())
        self.assertTrue((b[4 + 0, 0:2] == 0).all())
        self.assertTrue((b[4 + 0, 2:4] == B.NEG).all())

    def test_two_globals(self):
        spatial = torch.cat([torch.full((1, 2, 4), 0.5), halves(), torch.full((1, 2, 4), 0.25)], dim=0)
        masks = B.resize_masks(spatial, 2, 4)
        seg_lens, is_global = [3, 2, 2, 1], [True, False, False, True]
        b = B.build_bias(seg_lens, masks, is_global, True)
        T = sum(seg_lens)
        self.assertTrue((b[3:5, 7:8] == 0).all())  # left text reads the last global
        self.assertTrue((b[7:8, 0:3] == 0).all())  # globals read each other
        self.assertAlmostEqual(b[T + 0, 7].item(), math.log(0.25), places=5)
        self.assertEqual(b[T + 0, T + 7].item(), B.NEG)  # gating still blocks across halves

    def test_weight_above_one_is_positive_bias(self):
        masks = self.masks.clone()
        masks[1] = masks[1] * 2.0
        b = self.bias(masks=masks)
        self.assertAlmostEqual(b[self.T + 0, 3].item(), math.log(2.0), places=5)
        self.assertAlmostEqual(b[3, self.T + 0].item(), math.log(2.0), places=5)


class PadAligned(unittest.TestCase):
    def test_view_shape_and_stride(self):
        b = torch.zeros(13, 13)
        out = B.pad_aligned(b, torch.float32, torch.device("cpu"))
        self.assertEqual(tuple(out.shape), (1, 1, 13, 13))
        self.assertEqual(out.stride(-2), 16)
        self.assertTrue(torch.equal(out[0, 0], b))


if __name__ == "__main__":
    unittest.main()
