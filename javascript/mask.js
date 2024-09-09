class ForgeCoupleMaskHandler {

    #group = undefined;
    #gallery = undefined;
    #preview = undefined;
    separatorField = undefined;
    #background = undefined;
    #promptField = undefined;
    #weightField = undefined;
    #operationField = undefined;
    #operationButton = undefined;
    #loadButton = undefined;

    /** @returns {string} */
    get #sep() {
        var sep = this.separatorField.value.trim();
        sep = (!sep) ? "\n" : sep.replace(/\\n/g, "\n").replace(/\\t/g, "\t");
        return sep;
    }

    /** @returns {boolean} */
    get #selectionAvailable() { return !(this.#loadButton.disabled); }

    /**
     * @param {HTMLDivElement} group
     * @param {HTMLDivElement} gallery
     * @param {HTMLDivElement} preview
     * @param {HTMLInputElement} sep
     * @param {HTMLInputElement} background
     * @param {HTMLTextAreaElement} promptField
     * @param {HTMLTextAreaElement} op
     * @param {HTMLButtonElement} opButton
     * @param {HTMLButtonElement} loadButton
     */
    constructor(group, gallery, preview, sep, background, promptField, weightField, op, opButton, loadButton) {
        this.#group = group;
        this.#gallery = gallery;
        this.#preview = preview;
        this.separatorField = sep;
        this.#background = background;
        this.#promptField = promptField;
        this.#weightField = weightField;
        this.#operationField = op;
        this.#operationButton = opButton;
        this.#loadButton = loadButton;
    }

    /** @returns {HTMLDivElement[]} */
    get #allRows() {
        return this.#preview.querySelectorAll(".fc_mask_row");
    }

    hideButtons() {
        const undo = this.#group.querySelector("button[aria-label='Undo']");
        if (undo == null || undo.style.display === "none")
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
        this.syncPrompts();
        this.parseWeights();

        if (!this.#selectionAvailable) {
            const lastSelected = this.#preview.querySelector(".selected");
            if (lastSelected) lastSelected.classList.remove("selected");
        }
    }

    /** @param {HTMLDivElement} row */
    #constructRow(row) {
        if (row.hasOwnProperty("setup"))
            return;

        const img = document.createElement("img");
        img.setAttribute('style', 'width: 96px !important; height: 96px !important; object-fit: contain;');
        row.appendChild(img);
        row.img = img;

        img.addEventListener("click", () => { this.#onSelectRow(row); });

        const txt = document.createElement("input");
        txt.setAttribute('style', 'width: 80%;');
        txt.setAttribute("type", "text");
        row.appendChild(txt);
        row.txt = txt;

        txt.value = "";
        txt.addEventListener("blur", () => { this.#onSubmitPrompt(txt); });

        const weight = document.createElement("input");
        weight.setAttribute('style', 'width: 10%;');
        weight.setAttribute("type", "number");
        row.appendChild(weight);
        row.weight = weight;

        weight.value = Number(1.0).toFixed(2);
        weight.addEventListener("blur", () => { this.#onSubmitWeight(weight); });

        const del = document.createElement("button");
        del.classList.add("del");
        del.textContent = "❌";
        row.appendChild(del);

        del.addEventListener("click", () => { this.#onDeleteRow(row); });

        const up = document.createElement("button");
        up.classList.add("up");
        up.textContent = "^";
        row.appendChild(up);

        up.addEventListener("click", () => { this.#onShiftRow(row, true); });

        const down = document.createElement("button");
        down.classList.add("down");
        down.textContent = "^";
        row.appendChild(down);

        down.addEventListener("click", () => { this.#onShiftRow(row, false); });

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

    /** @param {HTMLInputElement} field */
    #onSubmitPrompt(field) {
        const prompts = [];
        this.#allRows.forEach((row) => {
            prompts.push(row.txt.value);
        });

        const radio = this.#background.querySelector('div.wrap>label.selected>span');
        const background = radio.textContent;

        if (background != "None") {
            const existingPrompt = this.#promptField.value
                .split(this.#sep).map(line => line.trim());

            if (background == "First Line")
                prompts.unshift(existingPrompt[0]);
            else
                prompts.push(existingPrompt[existingPrompt.length - 1]);
        }

        this.#promptField.value = prompts.join(this.#sep);
        updateInput(this.#promptField);
    }

    /** @param {HTMLInputElement} field */
    #onSubmitWeight(field) {
        const w = this.#clamp05(field.value);
        field.value = Number(w).toFixed(2);
        this.parseWeights();
    }

    /** @param {HTMLDivElement} row */
    #onSelectRow(row) {
        const rows = Array.from(this.#allRows);
        const index = rows.indexOf(row);

        const lastSelected = this.#preview.querySelector(".selected");
        if (lastSelected) lastSelected.classList.remove("selected");

        row.classList.add("selected");
        this.#operationField.value = `${index}`;
        updateInput(this.#operationField);
        this.#operationButton.click();
    }

    /** @param {HTMLDivElement} row */
    #onDeleteRow(row) {
        const rows = Array.from(this.#allRows);
        const index = rows.indexOf(row);

        this.#operationField.value = `-${index}`;
        updateInput(this.#operationField);
        this.#operationButton.click();
    }

    /** @param {HTMLDivElement} row @param {boolean} isUp */
    #onShiftRow(row, isUp) {
        const rows = Array.from(this.#allRows);
        const index = rows.indexOf(row);
        const target = isUp ? index - 1 : index + 1;

        if (target < 0 || target >= rows.length)
            return;

        this.#operationField.value = `${index}=${target}`;
        updateInput(this.#operationField);
        this.#operationButton.click();
    }

    syncPrompts() {
        const prompt = this.#promptField.value;
        var prompts = prompt.split(this.#sep).map(line => line.trim());

        const radio = this.#background.querySelector('div.wrap>label.selected>span');
        const background = radio.textContent;

        if (background == "First Line")
            prompts = prompts.slice(1);
        else if (background == "Last Line")
            prompts = prompts.slice(0, -1);

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

    parseWeights() {
        const weights = [];
        this.#allRows.forEach((row) => {
            weights.push(row.weight.value);
        });

        this.#weightField.value = weights.join(",");
        updateInput(this.#weightField);
    }

    /** @param {number} v @returns {number} */
    #clamp05(v) {
        var val = parseFloat(v);
        if (Number.isNaN(val))
            val = 0.0;

        return Math.min(Math.max(val, 0.0), 5.0);
    }
}
