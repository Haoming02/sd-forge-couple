class ForgeCoupleMaskHandler {

    #group = undefined;
    #gallery = undefined;
    #preview = undefined;
    #sep = undefined;
    #background = undefined;
    #promptField = undefined;

    /**
     * @param {HTMLDivElement} group
     * @param {HTMLDivElement} gallery
     * @param {HTMLDivElement} preview
     * @param {HTMLInputElement} sep
     * @param {HTMLInputElement} background
     * @param {HTMLTextAreaElement} promptField
     */
    constructor(group, gallery, preview, sep, background, promptField) {
        this.#group = group;
        this.#gallery = gallery;
        this.#preview = preview;
        this.#sep = sep;
        this.#background = background;
        this.#promptField = promptField;
    }

    /** @returns {HTMLDivElement[]} */
    get #allRows() {
        return this.#preview.querySelectorAll(".fc_mask_row");
    }

    hideButtons() {
        const undo = this.#group.querySelector("button[aria-label='Undo']");
        if (undo == null)
            return;

        undo.style.display = "none";

        const clear = this.#group.querySelector("button[aria-label='Clear']");
        clear.style.display = "none";

        const remove = this.#group.querySelector("button[aria-label='Remove Image']");
        remove.style.display = "none";

        const brush = this.#group.querySelector("button[aria-label='Use brush']");
        brush.firstElementChild.style.width = "20px";
        brush.firstElementChild.style.height = "20px";

        const color = this.#group.querySelector("button[aria-label='Select brush color']");
        color.firstElementChild.style.width = "20px";
        color.firstElementChild.style.height = "20px";

        brush.parentElement.parentElement.style.top = "var(--size-2)";
        brush.parentElement.parentElement.style.right = "var(--size-10)";
    }

    generatePreview() {
        const imgs = this.#gallery.querySelectorAll("img");
        const maskCount = imgs.length;

        // Clear Excess Rows
        while (this.#preview.children.length > maskCount)
            this.#preview.lastElementChild.remove();

        // Append Insufficient Rows
        while (this.#preview.children.length < maskCount) {
            const row = document.createElement("div");
            row.classList.add("fc_mask_row");
            this.#preview.appendChild(row);
        }

        this.#populateRows(this.#allRows, imgs);
        this.syncPrompts(this.#allRows);
    }

    /** @param {HTMLDivElement} row */
    #constructRow(row) {
        if (row.hasOwnProperty("setup"))
            return;

        const img = document.createElement("img");
        img.setAttribute('style', 'width: 96px !important; height: 96px !important; object-fit: contain;');
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
    #populateRows(rows, imgs) {
        const len = rows.length;
        console.assert(len === imgs.length);

        for (let i = 0; i < len; i++) {
            this.#constructRow(rows[i]);
            rows[i].img.src = imgs[i].src;
        }
    }

    syncPrompts() {
        const prompt = this.#promptField.value;

        var sep = this.#sep.value.trim();
        if (!sep) sep = "\n";

        const prompts = prompt.split(sep).map(line => line.trim());

        const active = document.activeElement;
        this.#allRows.forEach((row, i) => {
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
