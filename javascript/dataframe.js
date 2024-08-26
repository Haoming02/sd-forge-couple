class ForgeCoupleDataframe {

    static #default_mapping = [
        [0.0, 0.5, 0.0, 1.0, 1.0],
        [0.5, 1.0, 0.0, 1.0, 1.0]
    ];

    static get #columns() { return this.#tableHeader.length; }

    static #tableHeader = ["x1", "x2", "y1", "y2", "w", "prompt"];
    static #tableWidth = ["6%", "6%", "6%", "6%", "6%", "70%"];

    static #colors = [0, 30, 60, 120, 240, 280, 320];
    static #color(i) { return `hsl(${ForgeCoupleDataframe.#colors[i % 7]}, 36%, 36%)` }

    /** "t2i" | "i2i" */
    #mode = undefined;
    #promptField = undefined;
    #separatorField = undefined;

    get #sep() {
        var sep = this.#separatorField.value.trim();
        sep = (!sep) ? "\n" : sep.replace(/\\n/g, "\n").replace(/\\t/g, "\t");
        return sep;
    }

    #body = undefined;
    #selection = -1;

    /** @param {Element} div @param {string} mode @param {Element} separator */
    constructor(div, mode, separator) {
        this.#mode = mode;
        this.#promptField = document.getElementById(`${mode === "t2i" ? "txt" : "img"}2img_prompt`).querySelector("textarea");
        this.#separatorField = separator;

        const table = document.createElement('table');


        const colgroup = document.createElement('colgroup');
        for (let c = 0; c < ForgeCoupleDataframe.#columns; c++) {
            const col = document.createElement('col');
            col.style.width = ForgeCoupleDataframe.#tableWidth[c];
            colgroup.appendChild(col);
        }
        table.appendChild(colgroup);


        const thead = document.createElement('thead');
        const thr = thead.insertRow();
        for (let c = 0; c < ForgeCoupleDataframe.#columns; c++) {
            const th = document.createElement('th');
            th.textContent = ForgeCoupleDataframe.#tableHeader[c];
            thr.appendChild(th);
        }
        table.appendChild(thead);


        const tbody = document.createElement('tbody');
        for (let r = 0; r < ForgeCoupleDataframe.#default_mapping.length; r++) {
            const tr = tbody.insertRow();

            for (let c = 0; c < ForgeCoupleDataframe.#columns; c++) {
                const td = tr.insertCell();
                const isPrompt = (c === ForgeCoupleDataframe.#columns - 1);

                td.contentEditable = true;
                td.textContent = isPrompt ? "" : Number(ForgeCoupleDataframe.#default_mapping[r][c]).toFixed(2);

                td.addEventListener("keydown", (e) => {
                    if (e.key == 'Enter') {
                        e.preventDefault();
                        td.blur();
                    }
                });

                td.addEventListener("blur", () => { this.#onSubmit(td, isPrompt); })
                td.onclick = () => { this.#onSelect(r); }
            }
        }
        table.appendChild(tbody);


        div.appendChild(table);
        this.#body = tbody;
    }

    /** @param {number} row */
    #onSelect(row) {
        this.#selection = (row === this.#selection) ? -1 : row;
        ForgeCouple.onSelect(this.#mode);
    }

    /** @param {Element} cell @param {boolean} isPrompt */
    #onSubmit(cell, isPrompt) {
        if (isPrompt) {
            const prompts = [];
            const rows = this.#body.querySelectorAll("tr");
            rows.forEach((row) => {
                const prompt = row.querySelector("td:last-child").textContent.trim();
                prompts.push(prompt);
            });

            const oldPrompts = this.#promptField.value.split(this.#sep).map(line => line.trim());
            const modified = prompts.length;

            if (modified >= oldPrompts.length)
                this.#promptField.value = prompts.join(this.#sep);
            else {
                const newPrompts = [...prompts, ...(oldPrompts.slice(modified))]
                this.#promptField.value = newPrompts.join(this.#sep);
            }

            updateInput(this.#promptField);
        } else {
            var val = this.#clamp01(cell.textContent,
                Array.from(cell.parentElement.children).indexOf(cell) === 4
            );
            val = Math.round(val / 0.01) * 0.01;
            cell.textContent = Number(val).toFixed(2);
            ForgeCouple.onSelect(this.#mode);
            ForgeCouple.onEntry(this.#mode);
        }
    }

    /** @param {number[][]} vals */
    onPaste(vals) {
        while (this.#body.querySelector("tr"))
            this.#body.deleteRow(0);

        const count = vals.length;

        for (let r = 0; r < count; r++) {
            const tr = this.#body.insertRow();

            for (let c = 0; c < ForgeCoupleDataframe.#columns; c++) {
                const td = tr.insertCell();
                const prompt = (c === ForgeCoupleDataframe.#columns - 1);

                td.contentEditable = true;
                td.textContent = prompt ? "" : Number(vals[r][c]).toFixed(2);

                td.addEventListener("keydown", (e) => {
                    if (e.key == 'Enter') {
                        e.preventDefault();
                        td.blur();
                    }
                });

                td.addEventListener("blur", () => { this.#onSubmit(td, prompt); })
                td.onclick = () => { this.#onSelect(r); }
            }
        }

        this.#selection = -1;
        ForgeCouple.onSelect(this.#mode);
        ForgeCouple.onEntry(this.#mode);
        this.syncPrompt();
    }

    reset() {
        while (this.#body.querySelector("tr"))
            this.#body.deleteRow(0);

        for (let r = 0; r < ForgeCoupleDataframe.#default_mapping.length; r++) {
            const tr = this.#body.insertRow();

            for (let c = 0; c < ForgeCoupleDataframe.#columns; c++) {
                const td = tr.insertCell();
                const prompt = (c === ForgeCoupleDataframe.#columns - 1);

                td.contentEditable = true;
                td.textContent = prompt ? "" : Number(ForgeCoupleDataframe.#default_mapping[r][c]).toFixed(2);

                td.addEventListener("keydown", (e) => {
                    if (e.key == 'Enter') {
                        e.preventDefault();
                        td.blur();
                    }
                });

                td.addEventListener("blur", () => { this.#onSubmit(td, prompt); })
                td.onclick = () => { this.#onSelect(r); }
            }
        }

        this.#selection = -1;
        ForgeCouple.onSelect(this.#mode);
        ForgeCouple.onEntry(this.#mode);
        this.syncPrompt();
    }

    /** @returns {number[][]} */
    #newRow() {
        const rows = this.#body.querySelectorAll("tr");
        const count = rows.length;

        const vals = Array.from(rows, row => {
            return Array.from(row.querySelectorAll("td"))
                .slice(0, -1).map(cell => parseFloat(cell.textContent));
        });

        const tr = this.#body.insertRow();

        for (let c = 0; c < ForgeCoupleDataframe.#columns; c++) {
            const td = tr.insertCell();
            const prompt = (c === ForgeCoupleDataframe.#columns - 1);

            td.contentEditable = true;
            td.textContent = "";

            td.addEventListener("keydown", (e) => {
                if (e.key == 'Enter') {
                    e.preventDefault();
                    td.blur();
                }
            });

            td.addEventListener("blur", () => { this.#onSubmit(td, prompt); })
            td.onclick = () => { this.#onSelect(count); }
        }

        return vals;
    }

    /** @param {boolean} newline */
    newRowAbove(newline) {
        const vals = this.#newRow();

        const newVals = [
            ...vals.slice(0, this.#selection),
            [0.0, 1.0, 0.0, 1.0, 1.0],
            ...vals.slice(this.#selection)
        ];

        const count = newVals.length;
        const rows = this.#body.querySelectorAll("tr");

        for (let r = 0; r < count; r++) {
            const cells = rows[r].querySelectorAll("td");
            for (let c = 0; c < ForgeCoupleDataframe.#columns - 1; c++)
                cells[c].textContent = Number(newVals[r][c]).toFixed(2);
        }

        if (newline) {
            const prompts = this.#promptField.value.split(this.#sep).map(line => line.trim());
            const newPrompts = [
                ...prompts.slice(0, this.#selection),
                "",
                ...prompts.slice(this.#selection)
            ];
            this.#promptField.value = newPrompts.join(this.#sep);
            updateInput(this.#promptField);
        }

        this.#selection += 1;
        ForgeCouple.onSelect(this.#mode);
        ForgeCouple.onEntry(this.#mode);
        this.syncPrompt();
    }

    /** @param {boolean} newline */
    newRowBelow(newline) {
        const vals = this.#newRow();

        const newVals = [
            ...vals.slice(0, this.#selection + 1),
            [0.25, 0.75, 0.25, 0.75, 1.0],
            ...vals.slice(this.#selection + 1)
        ];

        const count = newVals.length;
        const rows = this.#body.querySelectorAll("tr");

        for (let r = 0; r < count; r++) {
            const cells = rows[r].querySelectorAll("td");
            for (let c = 0; c < ForgeCoupleDataframe.#columns - 1; c++)
                cells[c].textContent = Number(newVals[r][c]).toFixed(2);
        }

        if (newline) {
            const prompts = this.#promptField.value.split(this.#sep).map(line => line.trim());
            const newPrompts = [
                ...prompts.slice(0, this.#selection + 1),
                "",
                ...prompts.slice(this.#selection + 1)
            ];
            this.#promptField.value = newPrompts.join(this.#sep);
            updateInput(this.#promptField);
        }

        ForgeCouple.onSelect(this.#mode);
        ForgeCouple.onEntry(this.#mode);
        this.syncPrompt();
    }

    /** @param {boolean} removeText */
    deleteRow(removeText) {
        const rows = this.#body.querySelectorAll("tr");
        const count = rows.length;

        const vals = Array.from(rows, row => {
            return Array.from(row.querySelectorAll("td"))
                .slice(0, -1).map(cell => parseFloat(cell.textContent));
        });

        vals.splice(this.#selection, 1);
        this.#body.deleteRow(count - 1);

        for (let r = 0; r < count - 1; r++) {
            const cells = rows[r].querySelectorAll("td");
            for (let c = 0; c < ForgeCoupleDataframe.#columns - 1; c++)
                cells[c].textContent = Number(vals[r][c]).toFixed(2);
        }

        if (removeText) {
            const prompts = this.#promptField.value.split(this.#sep).map(line => line.trim());
            prompts.splice(this.#selection, 1);
            this.#promptField.value = prompts.join(this.#sep);
            updateInput(this.#promptField);
        }

        if (this.#selection == count - 1)
            this.#selection -= 1;

        ForgeCouple.onSelect(this.#mode);
        ForgeCouple.onEntry(this.#mode);
        this.syncPrompt();
    }

    /** @returns {[string, Element]} */
    updateColors() {
        const rows = this.#body.querySelectorAll("tr");

        rows.forEach((row, i) => {
            const color = ForgeCoupleDataframe.#color(i);
            const stripe = (this.#selection === i) ? "var(--table-row-focus)" :
                `var(--table-${(i % 2 == 0) ? "odd" : "even"}-background-fill)`;

            row.style.background = `linear-gradient(to right, ${stripe} 80%, ${color})`;
        });

        if (this.#selection < 0 || this.#selection > rows.length)
            return [null, null];
        else
            return [ForgeCoupleDataframe.#color(this.#selection), rows[this.#selection]];
    }

    syncPrompt() {
        const prompt = this.#promptField.value;

        const prompts = prompt.split(this.#sep).map(line => line.trim());
        const rows = this.#body.querySelectorAll("tr");

        const active = document.activeElement;
        rows.forEach((row, i) => {
            const promptCell = row.querySelector("td:last-child");

            // Skip editing Cell
            if (promptCell === active)
                return;

            if (i < prompts.length)
                promptCell.textContent = prompts[i];
            else
                promptCell.textContent = "";
        });
    }

    /** @param {number} @param {boolean} w @returns {number} */
    #clamp01(v, w) {
        var val = parseFloat(v);
        if (Number.isNaN(val))
            val = 0.0;

        return Math.min(Math.max(val, 0.0), w ? 5.0 : 1.0);
    }

}
