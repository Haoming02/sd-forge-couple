class ForgeCouple {

    static previewRes = {};
    static previewBtn = {};
    static mappingTable = {};
    static manualIndex = {};
    static bbox = {};

    static coords = [[-1, -1], [-1, -1]];

    static COLORS = [
        "hsl(0, 36%, 36%)",
        "hsl(30, 36%, 36%)",
        "hsl(60, 36%, 36%)",
        "hsl(120, 36%, 36%)",
        "hsl(240, 36%, 36%)",
        "hsl(280, 36%, 36%)",
        "hsl(320, 36%, 36%)"
    ];

    /**
     * Update the color of the rows based on the order and selection
     * @param {string} mode "t2i" | "i2i"
     */
    static updateColors(mode) {
        const selection = parseInt(this.manualIndex[mode].value);

        const rows = this.mappingTable[mode].querySelectorAll("tr");
        rows.forEach((row, i) => {
            const bg = (selection === i) ?
                "var(--table-row-focus)" :
                `var(--table-${(i % 2 == 0) ? "odd" : "even"}-background-fill)`;
            row.style.background = `linear-gradient(to right, ${bg} 80%, ${this.COLORS[i % this.COLORS.length]})`;
        });

        if (selection < 0 || selection >= rows.length)
            ForgeCouple.bbox[mode].hideBox();
        else
            ForgeCouple.bbox[mode].showBox(this.COLORS[selection], rows[selection]);
    }

    /**
     *  When updating the mappings, trigger a preview
     * @param {string} mode "t2i" | "i2i"
     */
    static async preview(mode) {
        if (!mode)
            return;

        setTimeout(async () => {
            var res = null;
            var file = null;

            if (mode === "t2i") {
                const w = parseInt(gradioApp().getElementById("txt2img_width").querySelector("input").value);
                const h = parseInt(gradioApp().getElementById("txt2img_height").querySelector("input").value);
                res = `${w}x${h}`;
            } else {
                const i2i_size = gradioApp().getElementById("img2img_column_size").querySelector(".tab-nav");

                if (mode !== "i2i") {
                    file = mode;
                    mode = "i2i";
                }

                if (i2i_size.children[0].classList.contains("selected")) {
                    // Resize to
                    const w = parseInt(gradioApp().getElementById("img2img_width").querySelector("input").value);
                    const h = parseInt(gradioApp().getElementById("img2img_height").querySelector("input").value);
                    res = `${w}x${h}`;
                } else {
                    // Resize by
                    if (file) {
                        const dim = await this.img2resolution(file);
                        res = `${dim.w}x${dim.h}`;
                    } else {
                        res = gradioApp().getElementById("img2img_scale_resolution_preview")?.querySelector(".resolution")?.textContent;
                        if (!res)
                            res = "1024x1024";
                    }
                }
            }

            this.previewRes[mode].value = res;
            updateInput(this.previewRes[mode]);

            this.previewBtn[mode].click();

        }, 50);
    }

    /**
     * When clicking on a row, update the index
     * @param {string} mode "t2i" | "i2i"
     */
    static onSelect(mode) {
        const rows = this.mappingTable[mode].querySelectorAll("tr");
        rows.forEach((row, i) => {
            if (row.querySelector(":focus-within") != null) {
                if (this.manualIndex[mode].value == i)
                    this.manualIndex[mode].value = -1;
                else
                    this.manualIndex[mode].value = i;

                updateInput(this.manualIndex[mode]);
            }
        });

        this.updateColors(mode);
    }

    /**
     * When hovering on a row, try to show the corresponding prompt
     * @param {string} mode "t2i" | "i2i"
     * @param {Element} separator
     */
    static registerHovering(mode, separator) {
        const promptHint = document.createElement("div");
        promptHint.classList.add("prompt-hint");

        const table = ForgeCouple.mappingTable[mode].parentElement.parentElement.parentElement;
        table.appendChild(promptHint);

        var showHint = true;

        table.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            showHint = !showHint;
        });

        ForgeCouple.mappingTable[mode].addEventListener('mousemove', (e) => {
            if (!showHint) {
                promptHint.style.display = 'none';
                return;
            }

            var el = e.target;

            while (el.tagName !== 'TR') {
                el = el.parentElement;
                if (el.tagName === 'TABLE') {
                    promptHint.style.display = 'none';
                    return;
                }
            }

            const prompt = gradioApp().getElementById(`${mode === "t2i" ? "txt" : "img"}2img_prompt`).querySelector("textarea").value;
            var sep = separator.value.trim();

            if (!sep)
                sep = "\n";

            const rows = [...ForgeCouple.mappingTable[mode].querySelectorAll("tr")];
            const rowIndex = rows.indexOf(el);

            if (!prompt.trim()) {
                promptHint.style.display = 'none';
                return;
            }

            if (rowIndex < prompt.split(sep).length)
                promptHint.innerHTML = prompt.split(sep)[rowIndex].replaceAll("<", "&lt;").replaceAll(">", "&gt;");
            else
                promptHint.innerHTML = '<p style="color:red;"><i>missing...</i></p>';

            promptHint.style.left = `calc(${e.clientX}px + 1em)`;
            promptHint.style.top = `calc(${e.clientY}px + 1em)`;

            promptHint.style.display = 'block';
        });

        ForgeCouple.mappingTable[mode].addEventListener('mouseleave', (e) => {
            promptHint.style.display = 'none';
        });
    }

    /** Hook some elements to automatically refresh the resolution */
    static registerResolutionHandles() {

        [["txt2img", "t2i"], ["img2img", "i2i"]].forEach(([tab, mode]) => {
            const btns = gradioApp().getElementById(`${tab}_dimensions_row`)?.querySelectorAll("button");
            if (btns != null)
                btns.forEach((btn) => { btn.onclick = () => { ForgeCouple.preview(mode); } });

            const width = gradioApp().getElementById(`${tab}_width`).querySelectorAll("input");
            const height = gradioApp().getElementById(`${tab}_height`).querySelectorAll("input");

            [...width, ...height].forEach((slider) => {
                slider.addEventListener("change", () => { ForgeCouple.preview(mode); });
            });
        });

        const i2i_size_btns = gradioApp().getElementById("img2img_column_size").querySelector(".tab-nav");
        i2i_size_btns.addEventListener("click", () => { ForgeCouple.preview("i2i"); });

        const tabs = gradioApp().querySelector('#tabs').querySelector('.tab-nav');
        tabs.addEventListener("click", () => {
            if (tabs.children[0].classList.contains("selected"))
                ForgeCouple.preview("t2i");
            if (tabs.children[1].classList.contains("selected"))
                ForgeCouple.preview("i2i");
        });

    }

    /**
     * Given an image, return the width and height
     * @param {string} b64 Image in base64 encoding
     * @returns {object} {w, h}
     */
    static img2resolution(b64) {
        return new Promise(function (resolved, rejected) {

            var i = new Image()
            i.onload = function () {
                resolved({ w: i.width, h: i.height })
            };
            i.src = b64;

        });
    }

}

onUiLoaded(async () => {
    ["t2i", "i2i"].forEach((mode) => {
        const ex = gradioApp().getElementById(`forge_couple_${mode}`);

        ForgeCouple.previewRes[mode] = ex.querySelector(".fc_preview_res").querySelector("input");
        ForgeCouple.previewBtn[mode] = ex.querySelector(".fc_preview_real");
        ForgeCouple.mappingTable[mode] = ex.querySelector(".fc_mapping").querySelector("tbody");
        ForgeCouple.manualIndex[mode] = ex.querySelector(".fc_index").querySelector("input");
        ForgeCouple.registerHovering(mode, ex.querySelector(".fc_separator").querySelector("input"));

        const row = ex.querySelector(".controls-wrap");
        row.remove();

        const mapping_div = ex.querySelector(".fc_mapping").children[1];
        const btns = ex.querySelector(".fc_map_btns");

        mapping_div.insertBefore(btns, mapping_div.children[1]);

        const preview_img = ex.querySelector("img");
        preview_img.ondragstart = (e) => { e.preventDefault(); return false; };

        const manual_field = ex.querySelector(".fc_manual_field").querySelector("input");

        ForgeCouple.bbox[mode] = new ForgeCoupleBox(preview_img, manual_field, mode);
        while (preview_img.parentElement.firstElementChild.tagName === "DIV")
            preview_img.parentElement.firstElementChild.remove();

        setTimeout(() => {
            ForgeCouple.preview(mode);
        }, 50);
    });

    ForgeCouple.registerResolutionHandles();

})
