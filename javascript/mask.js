class ForgeCoupleMaskHandler {

    static #group = { "t2i": undefined, "i2i": undefined };
    static #gallery = { "t2i": undefined, "i2i": undefined };
    static #div = { "t2i": undefined, "i2i": undefined };
    static #sep = { "t2i": undefined, "i2i": undefined };

    /**
     * @param {string} mode
     * @param {Element} group
     * @param {Element} gallery
     * @param {Element} div
     * @param {Element} sep
     */
    static setup(mode, group, gallery, div, sep) {
        this.#group[mode] = group;
        this.#gallery[mode] = gallery;
        this.#div[mode] = div;
        this.#sep[mode] = sep;
    }

    /** @param {string} mode "t2i" | "i2i" */
    static hideButtons(mode) {
        const undo = this.#group[mode].querySelector("button[aria-label='Undo']");
        if (undo == null)
            return;

        undo.style.display = "none";

        const clear = this.#group[mode].querySelector("button[aria-label='Clear']");
        clear.style.display = "none";

        const remove = this.#group[mode].querySelector("button[aria-label='Remove Image']");
        remove.style.display = "none";

        const brush = this.#group[mode].querySelector("button[aria-label='Use brush']");
        brush.firstElementChild.style.width = "20px";
        brush.firstElementChild.style.height = "20px";

        const color = this.#group[mode].querySelector("button[aria-label='Select brush color']");
        color.firstElementChild.style.width = "20px";
        color.firstElementChild.style.height = "20px";

        brush.parentElement.parentElement.style.top = "var(--size-2)";
        brush.parentElement.parentElement.style.right = "var(--size-10)";
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
