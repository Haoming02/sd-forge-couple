class ForgeCoupleMaskHandler {
	/** @type {HTMLDivElement} */ #group = undefined;
	/** @type {HTMLDivElement} */ #gallery = undefined;
	/** @type {HTMLDivElement} */ #preview = undefined;
	/** @type {HTMLInputElement} */ #separatorField = undefined;
	/** @type {HTMLInputElement} */ #background = undefined;
	/** @type {HTMLTextAreaElement} */ #promptField = undefined;
	/** @type {HTMLTextAreaElement} */ #weightField = undefined;
	/** @type {HTMLTextAreaElement} */ #operationField = undefined;
	/** @type {HTMLButtonElement} */ #operationButton = undefined;
	/** @type {HTMLButtonElement} */ #loadButton = undefined;

    constructor(group, gallery, preview, separatorField, background, promptField, weightField, operationField, operationButton, loadButton) {
        this.#group = group;
        this.#gallery = gallery;
        this.#preview = preview;
        this.#separatorField = separatorField;
        this.#background = background;
        this.#promptField = promptField;
        this.#weightField = weightField;
        this.#operationField = operationField;
        this.#operationButton = operationButton;
        this.#loadButton = loadButton;

        this.#separatorField.addEventListener("blur", () => { this.syncPrompts(); });
    }

    /** @returns {string} */
    get #separator() {
        const sep = this.#separatorField.value.trim();
        return !sep ? "\n" : sep.replace(/\\n/g, "\n").split("\n").map((c) => c.trim()).join("\n");
    }

    /** @returns {boolean} */
    get #selectionAvailable() {
        return !this.#loadButton.disabled;
    }

    /** @returns {HTMLDivElement[]} */
    get #allRows() {
        return Array.from(this.#preview.querySelectorAll(".fc_mask_row"));
    }

    hideButtons() {
        const undo = this.#group.querySelector("button[aria-label='Undo']");
        if (undo == null || undo.style.display === "none") return;

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
        while (this.#preview.children.length > maskCount) this.#preview.lastElementChild.remove();

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
        if (row.hasAttribute("setup")) return;

        const img = document.createElement("img");
        img.title = "Select this Mask";
        img.setAttribute("style", "width: 96px !important; height: 96px !important; object-fit: contain;");
        img.addEventListener("click", () => {
            this.#onSelectRow(row);
        });

        row.appendChild(img);
        row.img = img;

        const txt = document.createElement("input");
        txt.value = "";
        txt.setAttribute("style", "width: 80%;");
        txt.setAttribute("type", "text");
        txt.addEventListener("blur", () => { this.#onSubmitPrompt(); });

        row.appendChild(txt);
        row.txt = txt;

        const weight = document.createElement("input");
        weight.title = "Weight";
        weight.value = Number(1.0).toFixed(2);
        weight.setAttribute("style", "width: 10%;");
        weight.setAttribute("type", "number");
        weight.addEventListener("blur", () => {
            this.#onSubmitWeight(weight);
        });

        row.appendChild(weight);
        row.weight = weight;

        const del = document.createElement("button");
        del.classList.add("del");
        del.textContent = "❌";
        del.title = "Delete this Mask";
        del.addEventListener("click", () => {
            this.#onDeleteRow(row);
        });

        row.appendChild(del);

        const up = document.createElement("button");
        up.classList.add("up");
        up.textContent = "^";
        up.title = "Move this Layer Up";
        up.addEventListener("click", () => {
            this.#onShiftRow(row, true);
        });

        row.appendChild(up);

        const down = document.createElement("button");
        down.classList.add("down");
        down.textContent = "^";
        down.title = "Move this Layer Down";
        down.addEventListener("click", () => {
            this.#onShiftRow(row, false);
        });

        row.appendChild(down);

        row.setAttribute("setup", true);
    }

    /** @param {HTMLDivElement[]} rows @param {HTMLImageElement[]} imgs */
    #populateRows(rows, imgs) {
        rows.forEach((row, i) => {
            this.#constructRow(row);
            row.img.src = imgs[i].src;
        });
    }

    #onSubmitPrompt() {
        const prompts = this.#allRows.map((row) => row.txt.value);

        const radio = this.#background.querySelector("div.wrap>label.selected>span");
        const background = radio.textContent;

        const existingPrompts = this.#promptField.value.split(this.#separator).map((line) => line.trim());

        if (existingPrompts.length > 0) {
            if (background === "First Line") prompts.unshift(existingPrompts.shift());
            else if (background === "Last Line") prompts.push(existingPrompts.pop());
        }

        const oldLen = existingPrompts.length;
        const newLen = prompts.length;

        if (newLen >= oldLen || oldLen === 0) {
            this.#promptField.value = prompts.join(this.#separator);
            updateInput(this.#promptField);
        } else {
            const newPrompts = [...prompts, ...existingPrompts.slice(newLen)];
            this.#promptField.value = newPrompts.join(this.#separator);
            updateInput(this.#promptField);
        }
    }

    /** @param {HTMLInputElement} field */
    #onSubmitWeight(field) {
        const w = this.#clamp05(field.value);
        field.value = w.toFixed(2);
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

        if (target < 0 || target >= rows.length) return;

        this.#operationField.value = `${index}=${target}`;
        updateInput(this.#operationField);
        this.#operationButton.click();
    }

    syncPrompts() {
        const prompt = this.#promptField.value;
        let prompts = prompt.split(this.#separator).map((line) => line.trim());

        const radio = this.#background.querySelector("div.wrap>label.selected>span");
        const background = radio.textContent;

        if (background === "First Line") prompts = prompts.slice(1);
        else if (background === "Last Line") prompts = prompts.slice(0, -1);

        const active = document.activeElement;
        this.#allRows.forEach((row, i) => {
            const promptCell = row.txt;

            // Skip the Cell being Edited
            if (promptCell === active) return;

            promptCell.value = i < prompts.length ? prompts[i].replace(/\n+/g, ", ").replace(/,+/g, ",") : "";
        });
    }

    parseWeights() {
        const weights = this.#allRows.map((row) => row.weight.value);
        this.#weightField.value = weights.join(",");
        updateInput(this.#weightField);
    }

    /** @param {number} v @returns {number} */
    #clamp05(v) {
        const val = parseFloat(v);
        if (Number.isNaN(val)) return 0.0;
        return Math.min(Math.max(val, 0.0), 5.0);
    }
}
