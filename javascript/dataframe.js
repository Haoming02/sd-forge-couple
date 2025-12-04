class ForgeCoupleDataframe {
    static #tableHeader = Object.freeze(["x1", "x2", "y1", "y2", "w", "prompt"]);
    static #tableWidth = Object.freeze(["6%", "6%", "6%", "6%", "6%", "70%"]);
    static #defaultMapping = Object.freeze([
        [(0.0).toFixed(2), (0.5).toFixed(2), (0.0).toFixed(2), (1.0).toFixed(2), (1.0).toFixed(2), ""],
        [(0.5).toFixed(2), (1.0).toFixed(2), (0.0).toFixed(2), (1.0).toFixed(2), (1.0).toFixed(2), ""],
    ]);

    static get #columnCount() { return this.#tableHeader.length; }
    static #colors = Object.freeze([0, 30, 60, 120, 240, 280, 320]);
    static #color(i) { return `hsl(${ForgeCoupleDataframe.#colors[i % 7]}, 36%, 36%)`; }

    /** @type {string} "t2i" | "i2i" */
    #mode = undefined;
    /** @type {HTMLTextAreaElement} */
    #promptField = undefined;
    /** @type {HTMLInputElement} */
    #separatorField = undefined;
    /** @type {HTMLTableElement} */
    #body = undefined;

    /** @type {number} */
    #selection = -1;

    constructor(div, mode, separatorField) {
        this.#mode = mode;
        this.#promptField = document
            .getElementById(`${mode === "t2i" ? "txt" : "img"}2img_prompt`)
            .querySelector("textarea");
        this.#separatorField = separatorField;

        this.#separatorField.addEventListener("blur", () => { this.syncPrompts(); });
        const table = document.createElement("table");

        const colGroup = document.createElement("colgroup");
        for (let c = 0; c < ForgeCoupleDataframe.#columnCount; c++) {
            const col = document.createElement("col");
            col.style.width = ForgeCoupleDataframe.#tableWidth[c];
            colGroup.appendChild(col);
        }
        table.appendChild(colGroup);

        const tHead = document.createElement("thead");
        const thRow = tHead.insertRow();
        for (let c = 0; c < ForgeCoupleDataframe.#columnCount; c++) {
            const th = document.createElement("th");
            th.textContent = ForgeCoupleDataframe.#tableHeader[c];
            thRow.appendChild(th);
        }
        table.appendChild(tHead);

        const tBody = document.createElement("tbody");
        for (let r = 0; r < ForgeCoupleDataframe.#defaultMapping.length; r++) {
            const tr = tBody.insertRow();
            for (let c = 0; c < ForgeCoupleDataframe.#columnCount; c++) {
                const td = tr.insertCell();
                td.contentEditable = true;
                td.textContent = ForgeCoupleDataframe.#defaultMapping[r][c];

                td.addEventListener("keydown", (e) => {
                    if (e.key === "Enter") {
                        e.preventDefault();
                        td.blur();
                    }
                });

                const isPrompt = c === ForgeCoupleDataframe.#columnCount - 1;
                td.onblur = () => { this.#onSubmit(td, isPrompt); };
                td.onclick = () => { this.#onSelect(r); };
            }
        }
        table.appendChild(tBody);

        div.appendChild(table);
        this.#body = tBody;
    }

    /** @returns {string} */
    get #separator() {
        const sep = this.#separatorField.value.trim();
        return !sep ? "\n" : sep.replace(/\\n/g, "\n").split("\n").map((c) => c.trim()).join("\n");
    }

    /** @param {number} row */
    #onSelect(row) {
        this.#selection = row === this.#selection ? -1 : row;
        ForgeCouple.onSelect(this.#mode);
    }

    /** @param {HTMLTableCellElement} cell @param {boolean} isPrompt */
    #onSubmit(cell, isPrompt) {
        if (isPrompt) {
            const prompts = [];
            const rows = this.#body.querySelectorAll("tr");
            rows.forEach((row) => {
                const prompt = row.querySelector("td:last-child").textContent.trim();
                prompts.push(opts.fc_adv_newline ? prompt.replaceAll("\\n", "\n") : prompt);
            });

            const oldPrompts = this.#promptField.value.split(this.#separator).map((line) => line.trim());
            const modified = prompts.length;

            if (modified >= oldPrompts.length) this.#promptField.value = prompts.join(this.#separator);
            else {
                const newPrompts = [...prompts, ...oldPrompts.slice(modified)];
                this.#promptField.value = newPrompts.join(this.#separator);
            }

            updateInput(this.#promptField);
        } else {
            const val = this.#clamp01(
                cell.textContent,
                Array.from(cell.parentElement.children).indexOf(cell) === ForgeCoupleDataframe.#columnCount - 1,
            ).toFixed(2);
            cell.textContent = val;
            ForgeCouple.onSelect(this.#mode);
            ForgeCouple.onEntry(this.#mode);
        }
    }

    /** @param {number[][]} vals */
    onPaste(vals) {
        while (this.#body.querySelector("tr")) this.#body.deleteRow(0);

        for (let r = 0; r < vals.length; r++) {
            const tr = this.#body.insertRow();

            for (let c = 0; c < ForgeCoupleDataframe.#columnCount; c++) {
                const td = tr.insertCell();
                td.contentEditable = true;

                const isPrompt = c === ForgeCoupleDataframe.#columnCount - 1;
                td.textContent = isPrompt ? "" : Number(vals[r][c]).toFixed(2);

                td.addEventListener("keydown", (e) => {
                    if (e.key === "Enter") {
                        e.preventDefault();
                        td.blur();
                    }
                });

                td.onblur = () => { this.#onSubmit(td, isPrompt); };
                td.onclick = () => { this.#onSelect(r); };
            }
        }

        this.#selection = -1;
        ForgeCouple.onSelect(this.#mode);
        ForgeCouple.onEntry(this.#mode);
        this.syncPrompts();
    }

    reset() {
        while (this.#body.querySelector("tr")) this.#body.deleteRow(0);

        for (let r = 0; r < ForgeCoupleDataframe.#defaultMapping.length; r++) {
            const tr = this.#body.insertRow();

            for (let c = 0; c < ForgeCoupleDataframe.#columnCount; c++) {
                const td = tr.insertCell();
                td.contentEditable = true;
                td.textContent = ForgeCoupleDataframe.#defaultMapping[r][c];

                td.addEventListener("keydown", (e) => {
                    if (e.key === "Enter") {
                        e.preventDefault();
                        td.blur();
                    }
                });

                const isPrompt = c === ForgeCoupleDataframe.#columnCount - 1;
                td.onblur = () => { this.#onSubmit(td, isPrompt); };
                td.onclick = () => { this.#onSelect(r); };
            }
        }

        this.#selection = -1;
        ForgeCouple.onSelect(this.#mode);
        ForgeCouple.onEntry(this.#mode);
        this.syncPrompts();
    }

    /** @returns {number[][]} */
    #newRow() {
        const rows = this.#body.querySelectorAll("tr");
        const count = rows.length;

        const vals = Array.from(rows, (row) => {
            return Array.from(row.querySelectorAll("td"))
                .slice(0, -1)
                .map((cell) => parseFloat(cell.textContent));
        });

        const tr = this.#body.insertRow();

        for (let c = 0; c < ForgeCoupleDataframe.#columnCount; c++) {
            const td = tr.insertCell();
            td.contentEditable = true;
            td.textContent = "";

            td.addEventListener("keydown", (e) => {
                if (e.key === "Enter") {
                    e.preventDefault();
                    td.blur();
                }
            });

            const isPrompt = c === ForgeCoupleDataframe.#columnCount - 1;
            td.onblur = () => { this.#onSubmit(td, isPrompt); };
            td.onclick = () => { this.#onSelect(count); };
        }

        return vals;
    }

    /** @param {boolean} newline */
    newRowAbove(newline) {
        const vals = this.#newRow();

        const newVals = [
            ...vals.slice(0, this.#selection),
            [0.0, 1.0, 0.0, 1.0, 1.0],
            ...vals.slice(this.#selection),
        ];

        const count = newVals.length;
        const rows = this.#body.querySelectorAll("tr");

        for (let r = 0; r < count; r++) {
            const cells = rows[r].querySelectorAll("td");
            for (let c = 0; c < ForgeCoupleDataframe.#columnCount - 1; c++)
                cells[c].textContent = Number(newVals[r][c]).toFixed(2);
        }

        if (newline) {
            const prompts = this.#promptField.value.split(this.#separator).map((line) => line.trim());
            const newPrompts = [...prompts.slice(0, this.#selection), "", ...prompts.slice(this.#selection)];
            this.#promptField.value = newPrompts.join(this.#separator);
            updateInput(this.#promptField);
        }

        this.#selection += 1;
        ForgeCouple.onSelect(this.#mode);
        ForgeCouple.onEntry(this.#mode);
        this.syncPrompts();
    }

    /** @param {boolean} newline */
    newRowBelow(newline) {
        const vals = this.#newRow();

        const newVals = [
            ...vals.slice(0, this.#selection + 1),
            [0.25, 0.75, 0.25, 0.75, 1.0],
            ...vals.slice(this.#selection + 1),
        ];

        const count = newVals.length;
        const rows = this.#body.querySelectorAll("tr");

        for (let r = 0; r < count; r++) {
            const cells = rows[r].querySelectorAll("td");
            for (let c = 0; c < ForgeCoupleDataframe.#columnCount - 1; c++)
                cells[c].textContent = Number(newVals[r][c]).toFixed(2);
        }

        if (newline) {
            const prompts = this.#promptField.value.split(this.#separator).map((line) => line.trim());
            const newPrompts = [...prompts.slice(0, this.#selection + 1), "", ...prompts.slice(this.#selection + 1)];
            this.#promptField.value = newPrompts.join(this.#separator);
            updateInput(this.#promptField);
        }

        ForgeCouple.onSelect(this.#mode);
        ForgeCouple.onEntry(this.#mode);
        this.syncPrompts();
    }

    /** @param {boolean} removeText */
    deleteRow(removeText) {
        const rows = this.#body.querySelectorAll("tr");
        const count = rows.length;

        const vals = Array.from(rows, (row) => {
            return Array.from(row.querySelectorAll("td"))
                .slice(0, -1)
                .map((cell) => parseFloat(cell.textContent));
        });

        vals.splice(this.#selection, 1);
        this.#body.deleteRow(count - 1);

        for (let r = 0; r < count - 1; r++) {
            const cells = rows[r].querySelectorAll("td");
            for (let c = 0; c < ForgeCoupleDataframe.#columnCount - 1; c++)
                cells[c].textContent = Number(vals[r][c]).toFixed(2);
        }

        if (removeText) {
            const prompts = this.#promptField.value.split(this.#separator).map((line) => line.trim());
            prompts.splice(this.#selection, 1);
            this.#promptField.value = prompts.join(this.#separator);
            updateInput(this.#promptField);
        }

        if (this.#selection === count - 1) this.#selection -= 1;

        ForgeCouple.onSelect(this.#mode);
        ForgeCouple.onEntry(this.#mode);
        this.syncPrompts();
    }

    /** @returns {[string, Element]} */
    updateColors() {
        const rows = this.#body.querySelectorAll("tr");

        rows.forEach((row, i) => {
            const color = ForgeCoupleDataframe.#color(i);
            const stripe =
                this.#selection === i
                    ? "var(--table-row-focus)"
                    : `var(--table-${i % 2 === 0 ? "odd" : "even"}-background-fill)`;
            row.style.background = `linear-gradient(to right, ${stripe} 80%, ${color})`;
        });

        if (this.#selection < 0 || this.#selection > rows.length) return [null, null];
        else return [ForgeCoupleDataframe.#color(this.#selection), rows[this.#selection]];
    }

    syncPrompts() {
        const prompt = this.#promptField.value;

        const prompts = prompt.split(this.#separator);
        const rows = this.#body.querySelectorAll("tr");

        const active = document.activeElement;
        rows.forEach((row, i) => {
            const promptCell = row.querySelector("td:last-child");

            // Skip the Cell being Edited
            if (promptCell === active) return;

            if (i < prompts.length)
                if (opts.fc_adv_newline) promptCell.textContent = prompts[i].replaceAll("\n", "\\n");
                else promptCell.textContent = prompts[i].replace(/\n+/g, ", ").replace(/,+/g, ",").trim();
            else promptCell.textContent = "";
        });
    }

    /** @param {number} @param {boolean} w @returns {number} */
    #clamp01(v, w) {
        const val = parseFloat(v);
        if (Number.isNaN(val)) return 0.0;
        return Math.min(Math.max(val, 0.0), w ? 5.0 : 1.0);
    }
}
