class ForgeCoupleMaskHandler {

    static #gallery = { "t2i": undefined, "i2i": undefined };
    static #div = { "t2i": undefined, "i2i": undefined };
    static #sep = { "t2i": undefined, "i2i": undefined };

    /**
     * @param {string} mode
     * @param {Element} gallery
     * @param {Element} div
     * @param {Element} sep
     */
    static setup(mode, gallery, div, sep) {
        this.#gallery[mode] = gallery;
        this.#div[mode] = div;
        this.#sep[mode] = sep;
    }

    /**
     * After updating the masks, trigger a preview
     * @param {string} mode "t2i" | "i2i"
     */
    static generatePreview(mode) {

        const imgs = this.#gallery[mode].querySelectorAll("img");
        const maskCount = imgs.length;

        // Clear Excess Rows
        while (this.#div[mode].children.length > maskCount)
            this.#div[mode].lastElementChild.remove();

        // Append Insufficient Rows
        while (this.#div[mode].children.length < maskCount) {
            const row = document.createElement("div");
            row.classList.add("fc_mask_row");
            this.#div[mode].appendChild(row);
        }

        this.#populateRows(this.#div[mode].querySelectorAll(".fc_mask_row"), imgs);
        this.#syncPrompts(mode, this.#div[mode].querySelectorAll(".fc_mask_row"));
    }

    /** @param {HTMLDivElement[]} row */
    static #constructRow(row) {
        if (row.hasOwnProperty("setup"))
            return;

        const img = document.createElement("img");
        img.setAttribute('style', 'width: 96px !important; height: 96px !important;');
        row.appendChild(img);
        row.img = img;

        const txt = document.createElement("input");
        txt.setAttribute('style', 'width: 90%;');
        txt.setAttribute("type", "text");
        row.appendChild(txt);
        row.txt = txt;

        const weight = document.createElement("input");
        weight.setAttribute('style', 'width: 10%;');
        weight.setAttribute("type", "number");
        row.appendChild(weight);
        row.weight = weight;
        weight.value = Number(1.0).toFixed(2);

        row.setup = true;
    }

    /** @param {HTMLDivElement[]} rows @param {HTMLImageElement[]} imgs */
    static #populateRows(rows, imgs) {
        const len = rows.length;
        console.assert(len === imgs.length);

        for (let i = 0; i < len; i++) {
            this.#constructRow(rows[i]);
            rows[i].img.src = imgs[i].src;
        }
    }

    /** @param {string} mode @param {HTMLDivElement[]} rows */
    static #syncPrompts(mode, rows) {
        const prompt = document.getElementById(`${mode === "t2i" ? "txt" : "img"}2img_prompt`).querySelector("textarea").value;

        var sep = this.#sep[mode].value.trim();
        if (!sep) sep = "\n";

        const prompts = prompt.split(sep).map(line => line.trim());

        const active = document.activeElement;
        rows.forEach((row, i) => {
            const promptCell = row.txt;

            // Skip editing Cell
            if (promptCell === active)
                return;

            if (i < prompts.length)
                promptCell.value = prompts[i];
            else
                promptCell.value = "";
        });
    }
}
