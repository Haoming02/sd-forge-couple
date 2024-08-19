class ForgeCouple {

    /** The fc_mapping \<div\> */
    static container = { "t2i": undefined, "i2i": undefined };
    /** The actual \<tbody\> */
    static mappingTable = { "t2i": undefined, "i2i": undefined };

    /** The floating \<button\>s for row controls */
    static rowButtons = { "t2i": undefined, "i2i": undefined };

    /** The \<input\> for preview resolution */
    static previewResolution = { "t2i": undefined, "i2i": undefined };
    /** The \<button\> to trigger preview */
    static previewButton = { "t2i": undefined, "i2i": undefined };

    /** The ForgeCoupleDataframe class */
    static dataframe = { "t2i": undefined, "i2i": undefined };
    /** The ForgeCoupleBox class */
    static bbox = { "t2i": undefined, "i2i": undefined };

    /** The \<input\> for SendTo buttons */
    static pasteField = { "t2i": undefined, "i2i": undefined };
    /** The \<input\> for internal updates */
    static entryField = { "t2i": undefined, "i2i": undefined };

    /**
     * After updating the mappings, trigger a preview
     * @param {string} mode "t2i" | "i2i"
     */
    static async preview(mode) {

        setTimeout(async () => {
            var res = null;

            if (mode === "t2i") {
                const w = parseInt(gradioApp().getElementById("txt2img_width").querySelector("input").value);
                const h = parseInt(gradioApp().getElementById("txt2img_height").querySelector("input").value);
                res = `${w}x${h}`;
            } else {
                const i2i_size = gradioApp().getElementById("img2img_column_size").querySelector(".tab-nav");

                if (i2i_size.children[0].classList.contains("selected")) {
                    // Resize to
                    const w = parseInt(gradioApp().getElementById("img2img_width").querySelector("input").value);
                    const h = parseInt(gradioApp().getElementById("img2img_height").querySelector("input").value);
                    res = `${w}x${h}`;
                } else {
                    // Resize by
                    res = gradioApp().getElementById("img2img_scale_resolution_preview")?.querySelector(".resolution")?.textContent;
                }
            }

            res ??= "1024x1024";
            this.previewResolution[mode].value = res;
            updateInput(this.previewResolution[mode]);

            this.previewButton[mode].click();
        }, (mode === "t2i") ? 16 : 32);
    }

    /**
     * Update the color of the rows based on the order and selection
     * @param {string} mode "t2i" | "i2i"
     */
    static updateColors(mode) {
        const [color, row] = this.dataframe[mode].updateColors();

        if (color) {
            this.bbox[mode].showBox(color, row);
            return row;
        }
        else {
            this.bbox[mode].hideBox();
            this.rowButtons[mode].style.display = "none";
            return null;
        }
    }

    /**
     * When using SendTo buttons, refresh the table
     * @param {string} mode "t2i" | "i2i"
     */
    static onPaste(mode) {
        const vals = JSON.parse(this.pasteField[mode].value);
        this.dataframe[mode].onPaste(vals);
        this.preview(mode);
    }

    /**
     * When clicking on a row, update the index
     * @param {string} mode "t2i" | "i2i"
     */
    static onSelect(mode) {
        const cell = this.updateColors(mode);

        if (cell) {
            const bounding = cell.querySelector("td").getBoundingClientRect();
            const bounding_container = this.container[mode].getBoundingClientRect();
            this.rowButtons[mode].style.top = `calc(${bounding.top - bounding_container.top}px - 1.5em)`;
            this.rowButtons[mode].style.display = "block";
        } else
            this.rowButtons[mode].style.display = "none";
    }

    /**
     * When editing the mapping, update the internal JSON
     * @param {string} mode "t2i" | "i2i"
     */
    static onEntry(mode) {
        const rows = this.mappingTable[mode].querySelectorAll("tr");

        const vals = Array.from(rows, row => {
            return Array.from(row.querySelectorAll("td"))
                .slice(0, -1).map(cell => parseFloat(cell.textContent));
        });

        const json = JSON.stringify(vals);
        this.entryField[mode].value = json;
        updateInput(this.entryField[mode]);
    }

    /**
     * Link the buttons related to the mapping
     * @param {Element} ex
     * @param {string} mode "t2i" | "i2i"
     */
    static #registerButtons(ex, mode) {
        ex.querySelector(".fc_reset_btn").onclick = () => { this.dataframe[mode].reset(); };
        ex.querySelector("#fc_up_btn").onclick = (e) => { this.dataframe[mode].newRowAbove(e.shiftKey); };
        ex.querySelector("#fc_dn_btn").onclick = (e) => { this.dataframe[mode].newRowBelow(e.shiftKey); };
        ex.querySelector("#fc_del_btn").onclick = (e) => { this.dataframe[mode].deleteRow(e.shiftKey); };
    }

    /** Hook some elements to automatically refresh the resolution */
    static #registerResolutionHandles() {

        [["txt2img", "t2i"], ["img2img", "i2i"]].forEach(([tab, mode]) => {
            const btns = gradioApp().getElementById(`${tab}_dimensions_row`)?.querySelectorAll("button");
            if (btns != null)
                btns.forEach((btn) => { btn.onclick = () => { this.preview(mode); } });

            const width = gradioApp().getElementById(`${tab}_width`).querySelectorAll("input");
            const height = gradioApp().getElementById(`${tab}_height`).querySelectorAll("input");

            [...width, ...height].forEach((slider) => {
                slider.addEventListener("change", () => { this.preview(mode); });
            });
        });

        const i2i_size_btns = gradioApp().getElementById("img2img_column_size").querySelector(".tab-nav");
        i2i_size_btns.addEventListener("click", () => { this.preview("i2i"); });

        const tabs = gradioApp().querySelector('#tabs').querySelector('.tab-nav');
        tabs.addEventListener("click", () => {
            if (tabs.children[0].classList.contains("selected"))
                this.preview("t2i");
            if (tabs.children[1].classList.contains("selected"))
                this.preview("i2i");
        });

    }

    static setup() {
        ["t2i", "i2i"].forEach((mode) => {
            const ex = gradioApp().getElementById(`forge_couple_${mode}`);
            const mapping_btns = ex.querySelector(".fc_mapping_btns");

            this.container[mode] = ex.querySelector(".fc_mapping");
            this.container[mode].appendChild(mapping_btns);

            this.dataframe[mode] = new ForgeCoupleDataframe(
                this.container[mode], mode, ex.querySelector(".fc_separator").querySelector("input")
            );
            this.mappingTable[mode] = this.container[mode].querySelector("tbody");

            this.rowButtons[mode] = ex.querySelector(".fc_row_btns");
            this.rowButtons[mode].style.display = "none";
            this.container[mode].appendChild(this.rowButtons[mode]);

            this.previewResolution[mode] = ex.querySelector(".fc_preview_res").querySelector("input");
            this.previewButton[mode] = ex.querySelector(".fc_preview");

            const preview_img = ex.querySelector("img");
            preview_img.ondragstart = (e) => { e.preventDefault(); return false; };
            preview_img.parentElement.style.overflow = "visible";

            this.bbox[mode] = new ForgeCoupleBox(preview_img, mode);

            const bg_btns = ex.querySelector(".fc_bg_btns");
            preview_img.parentElement.appendChild(bg_btns);

            ForgeCoupleImageLoader.setup(preview_img, bg_btns.querySelectorAll("button"))

            this.pasteField[mode] = ex.querySelector(".fc_paste_field").querySelector("textarea");
            this.entryField[mode] = ex.querySelector(".fc_entry_field").querySelector("textarea");

            this.#registerButtons(ex, mode);
            ForgeCoupleObserver.observe(
                mode,
                gradioApp().getElementById(`${mode === "t2i" ? "txt" : "img"}2img_prompt`).querySelector("textarea"),
                () => { this.dataframe[mode].syncPrompt(); }
            );
        });

        this.#registerResolutionHandles();
    }

}

onUiLoaded(async () => { ForgeCouple.setup(); })
