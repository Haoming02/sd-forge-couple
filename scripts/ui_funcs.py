from json.decoder import JSONDecodeError
from PIL import Image, ImageDraw
from json import loads

DEFAULT_MAPPING = [["0.00:0.50", "0.00:1.00", "1.0"], ["0.50:1.00", "0.00:1.00", "1.0"]]
COLORS = ("red", "orange", "yellow", "green", "blue", "indigo", "violet")


def parse_mapping(data: list) -> list:
    mapping = []

    for [X, Y, W] in data:
        if not X.strip():
            continue

        mapping.append(
            (
                (float(X.split(":")[0]), float(X.split(":")[1])),
                (float(Y.split(":")[0]), float(Y.split(":")[1])),
                float(W),
            )
        )

    return mapping


def validate_mapping(data: list) -> bool:
    try:
        for [X, Y, W] in data:
            if not X.strip():
                continue

            assert len(X.split(":")) == 2
            assert len(Y.split(":")) == 2

            val = []

            val.append(float(X.split(":")[0]))
            val.append(float(X.split(":")[1]))
            val.append(float(Y.split(":")[0]))
            val.append(float(Y.split(":")[1]))
            float(W)

            for v in val:
                if v < 0.0 or v > 1.0:
                    raise OverflowError

            if val[1] < val[0] or val[3] < val[2]:
                raise IndexError

        return True

    except AssertionError:
        print("\n\n[Couple] Incorrect number of : in Mapping...\n\n")
        return False
    except ValueError:
        print("\n\n[Couple] Non-Number in Mapping...\n\n")
        return False
    except OverflowError:
        print("\n\n[Couple] Range must be between 0.0 and 1.0...\n\n")
        return False
    except IndexError:
        print('\n\n[Couple] "to" value must be larger than "from" value...\n\n')
        return False


def visualize_mapping(res: str, data: list) -> Image:
    w, h = res.split("x")
    p_WIDTH = int(w)
    p_HEIGHT = int(h)

    while p_WIDTH > 1024 or p_HEIGHT > 1024:
        p_WIDTH //= 2
        p_HEIGHT //= 2

    while p_WIDTH < 512 and p_HEIGHT < 512:
        p_WIDTH *= 2
        p_HEIGHT *= 2

    matt = Image.new("RGBA", (p_WIDTH, p_HEIGHT), (0, 0, 0, 64))

    if not (validate_mapping(data)):
        return matt

    lnw = int(max(min(p_WIDTH, p_HEIGHT) / 128, 4.0))

    draw = ImageDraw.Draw(matt)

    mapping = parse_mapping(data)

    # print("\nAdv. Preview:")
    for tile_index in range(len(mapping)):
        color_index = tile_index % len(COLORS)

        (X, Y, W) = mapping[tile_index]
        x_from = int(p_WIDTH * X[0])
        x_to = int(p_WIDTH * X[1])
        y_from = int(p_HEIGHT * Y[0])
        y_to = int(p_HEIGHT * Y[1])
        # weight = W

        # print(f"  [{y_from:4d}:{y_to:4d}, {x_from:4d}:{x_to:4d}] = {weight:.2f}")
        draw.rectangle(
            ((x_from, y_from), (x_to, y_to)), outline=COLORS[color_index], width=lnw
        )

    return matt


def reset_mapping() -> list:
    return DEFAULT_MAPPING


def add_row_above(data: list, index: int) -> list:
    if index < 0:
        return data
    return data[:index] + [["0.00:1.00", "0.00:1.00", "1.0"]] + data[index:]


def add_row_below(data: list, index: int) -> list:
    if index < 0:
        return data + [["0.25:0.75", "0.25:0.75", "1.0"]]
    return data[: index + 1] + [["0.25:0.75", "0.25:0.75", "1.0"]] + data[index + 1 :]


def del_row_select(data: list, index: int) -> list:
    if index < 0:
        return data
    if len(data) == 1:
        return [["0.0:1.0", "0.0:1.0", "1.0"]]
    else:
        del data[index]
        return data


def on_paste(data: str) -> list:
    try:
        return loads(data)
    except JSONDecodeError:
        print("\n[Adv. Mapping] Pasting Old Infotext is not supported...\n")
        return DEFAULT_MAPPING


def manual_entry(data: list, new: str, index: int) -> list:
    if index < 0:
        return data

    v = [round(float(val), 2) for val in new.split(",")]

    if v[1] < v[0]:
        v[0], v[1] = v[1], v[0]
    if v[3] < v[2]:
        v[2], v[3] = v[3], v[2]

    try:
        data[index][0] = f"{v[0]:.2f}:{v[1]:.2f}"
        data[index][1] = f"{v[2]:.2f}:{v[3]:.2f}"
    except IndexError:
        data.append([f"{v[0]:.2f}:{v[1]:.2f}", f"{v[2]:.2f}:{v[3]:.2f}", "1.0"])

    return data
