# SD Forge Attention Couple
This is an Extension for the [Forge Webui](https://github.com/lllyasviel/stable-diffusion-webui-forge), which allows you to ~~generate couples~~ target conditioning at different regions. No more color bleeds or mixed features!

> Compatible with both old & new Forge

> Does **not** work with [Automatic1111 Webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui)

> Supports both `SD 1.5` & `SDXL` checkpoints, but **not** `Flux`...

## Showcase

- Generate the following prompt using the [Juggernaut XL V7](https://civitai.com/models/133005/juggernaut-xl) checkpoint with same seed and parameters:

```
a cinematic photo of 2 men arguing, indoors, court room
2 men, jesus christ, white robe, looking at each other, shouting
2 men, santa claus, looking at each other, shouting
```

<table>
    <thead align="center">
        <tr>
            <td>Extension</td>
            <td><b>Disabled</b></td>
            <td><b>Enabled</b></td>
        </tr>
    </thead>
    <tbody align="center">
        <tr>
            <td>Result</td>
            <td><img src="example/off.jpg" width=384></td>
            <td><img src="example/on.jpg" width=384></td>
        </tr>
    </tbody>
</table>

- Notice the mixed features without the Extension; see the distinct "characters" when the Extension is enabled

## How to Use

> As shown in the various examples, even if a region only contains 1 subject, it usually works better to still prompt for the total amount of subjects first.

> **Note:** The effect of this Extension is still dependent on the prompt-adherence capability of the Checkpoint. If the checkpoint does not understand the composition, it still cannot generate the result correctly. Also, do not expect the composition to work every single time...

<details>
<summary><b>Index</b></summary>

- [Basic Mode](#basic-mode)
    - [Tile Direction](#tile-direction)
    - [Global Effect](#global-effect)
- [Advanced Mode](#advanced-mode)
- [Mask Mode](#mask-mode)
- Misc.
    - [Separator](#couple-separator)
    - [LoRA](#lora-support)
- [API](https://github.com/Haoming02/sd-forge-couple/wiki/API)

</details>

## Basic Mode

The **Basic** mode works by dividing the image into multiple "tiles" where each tile corresponding to one [line](#couple-separator) of the positive prompt. Therefore, simply prompt more lines if you want more regions.

<p align="center">
<img src="example/basic.jpg" width=384>
</p>

```
2girls, blonde twintails, cyan eyes, white serafuku, standing, waving, looking at viewer, smile
2girls, black long hair, red eyes, dark school uniform, standing, crossed arms, looking away
```

### Tile Direction

In the **Basic** mode, you can choose between whether to divie the image into columns or rows.

- **Horizontal:** First / Last line corresponds to the Left / Right region
- **Vertical:** First / Last line corresponds to the Top / Bottom region

<p align="center">
<img src="example/direction.jpg" width=384><br>
<b>Direction</b> set to <code>Vertical</code>
</p>

```
galaxy, stars, milky way
blue sky, clouds
sunrise, lens flare
ocean, waves
beach, sand
pavement, road
```

### Global Effect

In **Basic** and **Mask** modes, you can set either the **first** line or the **last** line of the positive prompt as the "background," affecting the entire image instead of just one region. Useful for specifying styles or quality tags used by **SD 1.5** and **Pony** checkpoints.

<br>

## Advanced Mode

Were these automated and equally-sized tiles not sufficient for your needs? Now you can manually specify each regions!

> **Important:** The entire image **must** contain weight. The easiest way would be adding a region that covers the whole image *(just like the **Global Effect** in **Basic**)*.

- **Entries:**
    - Each row contains a range for **x** axis, a range for **y** axis, a **weight**, as well as the corresponding **line** of prompt
    - The range should be within `0.0` ~ `1.0`, representing the **percentage** of the full width/height
        - **eg.** `0.0` to `1.0` would span across the entire axis
    - **x** axis is from left to right; **y** axis is from top to bottom
    - **2** *(to)* should be larger than **1** *(from)*

> **Note:** The mapping data is not sent when using the `Send to img2img` function. Click the `Pull from txt2img` to manually transfer the data. *(vice versa)*

- **Control:**
    - Click on a row to select it, highlighting its bounding box
        - Click on the same row again to deselect it
    - When a row is selected, click the `🆕` button above / below to insert a new row above / below
        - If holding `Shift`, it will also insert a newline to the prompts
    - When a row is selected, click the `❌` button to delete it
        - If holding `Shift`, it will also **delete** the corresponding line of prompt
    - Click the `Default Mapping` button to reset the mappings

- **Draggable Region:**
    - When a bounding box is highlighted, simply drag the box around to reposition the region; drag the edges / corners to resize the region

- **Background:**
    - Click the `📂` button to load a image as the background of the mapping
    - Click the `⏏` button to load the **img2img** input image as the background
    - Click the `🗑` button to clear the background

<p align="center">
<img src="example/adv_ui.jpg" width=384><br>
Advanced Mode UI<br>
<img src="example/adv_result.jpg" width=384><br>
Generation Result
</p>

```
a cinematic photo of a couple, from side, outdoors
couple photo, man, black tuxedo
couple photo, woman, white dress
wedding photo, holding flower bouquet together
sunset, golden hour, lens flare
```

<br>

## Mask Mode

<p align="right"><i><b>New</b> 🔥</i></p>

Were these bounding boxes still too rigid for you...? Now you can also manually draw the areas for each regions!

> **Important:** The entire image **must** contain weight. The easiest way would be using the **Global Effect**.

- **Canvas:**
    - Click the **Create Empty Canvas** button to generate a blank canvas to draw on
    - Only **pure white** `(255, 255, 255)` pixels count towards the mask, other colors are simply discarded
        - This also means that other colors can function as the "eraser" for the mask
    - Click the **Save Mask** button to save the image as a <ins>new</ins> layer of masks
    - When a layer is selected:
        - Click **Load Mask** to load the mask into canvas
        - Click **Override Mask** to save the image and <ins>override</ins> the selected layer of mask
    - Click the **Reset All Masks** button to clear all the data

> **Note:** The mask data is not sent when using the `Send to img2img` function. Click the `Pull from txt2img` to manually transfer the data. *(vice versa)*

- **Entries:**
    - Each row contains a **preview** of the layer, the corresponding **line** of prompt, and the **weight** for the layer
    - Click the preview image to <ins>select</ins> the layer
    - Use the arrow buttons to quickly re-order the layers
    - Click the `❌` button to delete the layer

- **Uploads:**
    - Use the `Upload Background` to upload an image as the reference to draw masks on
        - The image will get dimmed, therefore it will **not** count towards the mask
    - Use the `Upload Mask` to upload an image as a mask that can directly be saved
        - Mainly for when you prepare the masks in external programs

> **Note:** For `Gradio 3` *(Old Forge)* users, avoid pasting images, instead manually upload or simply drag & drop the images. Using `Ctrl + V` might send the image to the Canvas, thus breaking the Extension...

<p align="center">
<img src="example/mask_ui.jpg" width=512><br>
Mask Mode UI<br>
<img src="example/mask_result.jpg" width=512><br>
Generation Result
</p>

```
cinematic photo of a dungeon
glowing lit lamps
treasure chest
```

<br>

## Couple Separator

By default when the field is left empty, this Extension uses the newline character (`\n`) as the separator to determine "lines" of the prompts. You may also specify other words as the separator instead.

## LoRA Support

Using multiple LoRAs in different regions is possible, though it depends on how well the LoRAs work together...

LoRA that contains multiple subjects works better in my experience.

<p align="center">
<img src="example/lora.jpg" width=384>
</p>

```
[high quality, best quality], 2girls, on stage, backlighting, [bloom, hdr], <lora:suzurena:0.72>
2girls, miyama suzune, pink idol costume, feather hair ornament, holding hands, looking at viewer, smile, blush
2girls, hanaoi rena, blue idol costume, feather hair ornament, holding hands, looking at viewer, shy, blush
```

<br>

## API
For usage with API, please refer to the [Wiki](https://github.com/Haoming02/sd-forge-couple/wiki/API)

<hr>

## TypeError: 'NoneType'

For users that get the following error:

```py
RuntimeError: shape '[X, Y, 1]' is invalid for input of size Z
shape '[X, Y, 1]' is invalid for input of size Z
*** Error completing request
    ...
    Traceback (most recent call last):
        ...
        res = list(func(*args, **kwargs))
    TypeError: 'NoneType' object is not iterable
```

1. Go to **Settings** -> **Optimizations**, and enable `Pad prompt/negative prompt`
2. Set the `Width` and `Height` to multiple of **64**

<hr>

## Special Thanks
- Credits to the original author, **[laksjdjf](https://github.com/laksjdjf)**, whose [ComfyUI Node](https://github.com/laksjdjf/cgem156-ComfyUI/tree/main/scripts/attention_couple) I used to port into Forge
- Also check out <ins>arcusmaximus</ins>'s alternative approach to [draggable-box-ui](https://github.com/arcusmaximus/sd-forge-couple/tree/draggable-box-ui)
