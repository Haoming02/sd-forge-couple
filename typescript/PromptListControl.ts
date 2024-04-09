namespace ForgeCouple {
    interface TableRow {
        region: Region;
        rowElem: HTMLTableRowElement;
        colorElem: HTMLDivElement;
        promptElem: HTMLInputElement;
        weightElem: HTMLInputElement;
        deleteButtonElem: HTMLButtonElement;
    }

    export class PromptListControl {
        private static stylesheetCreated = false;
        private static readonly classNames = {
            addButton:   'forge-couple--prompt-list--add-button',
            table:       'forge-couple--prompt-list--table',
            colorCell:   'forge-couple--prompt-list--color-cell',
            colorMarker: 'forge-couple--prompt-list--color-marker',
            promptCell:  'forge-couple--prompt-list--prompt-cell',
            weightCell:  'forge-couple--prompt-list--weight-cell',
            deleteCell:  'forge-couple--prompt-list--delete-cell'
        };

        private addButtonElem: HTMLButtonElement;
        private tableElem: HTMLTableElement;
        private rows: TableRow[] = [];

        constructor(containerElem: HTMLElement, private maxRegions: number) {
            if (!PromptListControl.stylesheetCreated) {
                document.head.appendChild(this.createStylesheet());
                PromptListControl.stylesheetCreated = true;
            }

            this.addButtonElem = WebUI.createButton('Add region');
            this.addButtonElem.className += ' ' + PromptListControl.classNames.addButton;
            this.addButtonElem.addEventListener('click', _ => this.addRequested.next());
            containerElem.appendChild(this.addButtonElem);

            this.tableElem = document.createElement('table');
            this.tableElem.className = PromptListControl.classNames.table;
            containerElem.appendChild(this.tableElem);
        }

        public setRegions(regions: Region[]): void {
            for (let i = 0; i < regions.length; i++) {
                let row: TableRow;
                if (i < this.rows.length) {
                    row = this.rows[i];
                    row.region = regions[i];
                } else {
                    row = this.addGridRow(regions[i]);
                }
                this.updateTableRow(row);
            }

            while (this.rows.length > regions.length) {
                this.removeRegion(this.rows.length - 1);
            }

            this.updateAddButton();
        }

        public addRegion(region: Region) {
            this.addGridRow(region);
            this.updateAddButton();
            this.selectRegion(this.rows.length - 1);
        }

        public selectRegion(index: number): void {
            let row = this.rows[index];
            if (document.activeElement == row.promptElem)
                this.onPromptUpdated(row);
            else
                row.promptElem.focus();
        }

        public removeRegion(index: number): void {
            let row = this.rows.splice(index, 1)[0];
            row.rowElem.parentElement?.removeChild(row.rowElem);
            this.updateAddButton();
        }

        public addRequested = new Subject<void>();
        public regionSelected = new Subject<number>();
        public regionChanged = new Subject<number>();
        public removeRequested = new Subject<number>();

        private addGridRow(region: Region): TableRow {
            let rowElem = document.createElement('tr');
            rowElem.innerHTML = `
                <td class="${PromptListControl.classNames.colorCell}">
                    <div class="${PromptListControl.classNames.colorMarker}">
                    </div>
                </td>
                <td class="${PromptListControl.classNames.promptCell}">
                    <label class="${WebUI.inputClasses} container">
                        <input class="${WebUI.inputClasses}" placeholder="Prompt"/>
                    </label>
                </td>
                <td class="${PromptListControl.classNames.weightCell}">
                    <label class="${WebUI.inputClasses} container">
                        <input class="${WebUI.inputClasses}" placeholder="Weight"/>
                    </label>
                </td>
                <td class="${PromptListControl.classNames.deleteCell}">
                    <button class="${WebUI.buttonClasses}">❌</button>
                </td>
            `;
            let colorCell: HTMLTableCellElement | null    = rowElem.querySelector(`.${PromptListControl.classNames.colorCell}`);
            let colorElem: HTMLDivElement | null          = rowElem.querySelector(`.${PromptListControl.classNames.colorMarker}`);
            let promptElem: HTMLInputElement | null        = rowElem.querySelector(`.${PromptListControl.classNames.promptCell} input`);
            let weightElem: HTMLInputElement | null        = rowElem.querySelector(`.${PromptListControl.classNames.weightCell} input`);
            let deleteButtonElem: HTMLButtonElement | null = rowElem.querySelector(`.${PromptListControl.classNames.deleteCell} button`);
            if (!colorCell || !colorElem || !promptElem || !weightElem || !deleteButtonElem) {
                throw new Error('Forge Couple: Failed to create prompt row');
            }

            let row: TableRow = { region, rowElem, colorElem, promptElem, weightElem, deleteButtonElem };
            this.updateTableRow(row);

            colorCell.addEventListener('click', _ => this.onMarkerClicked(row));
            promptElem.addEventListener('focus', _ => this.onPromptFocused(row));
            promptElem.addEventListener('change', _ => this.onPromptUpdated(row));
            weightElem.addEventListener('change', _ => this.onWeightUpdated(row));
            deleteButtonElem.addEventListener('click', _ => this.onDeleteClicked(row));
            
            this.tableElem.appendChild(rowElem);
            this.rows.push(row);
            return row;
        }

        private updateTableRow(row: TableRow): void {
            row.colorElem.style.backgroundColor = row.region.enabled ? row.region.color : 'transparent';
            row.promptElem.value = row.region.prompt;
            row.weightElem.value = row.region.weight.toString();
        }

        private updateAddButton(): void {
            this.addButtonElem.disabled = this.rows.length >= this.maxRegions;
        }

        private onMarkerClicked(row: TableRow): void {
            row.region.enabled = !row.region.enabled;
            this.updateTableRow(row);
            this.regionChanged.next(this.rows.indexOf(row));
        }

        private onPromptFocused(row: TableRow): void {
            this.regionSelected.next(this.rows.indexOf(row));
        }

        private onPromptUpdated(row: TableRow): void {
            row.region.prompt = row.promptElem.value;
            this.regionChanged.next(this.rows.indexOf(row));
        }

        private onWeightUpdated(row: TableRow): void {
            let weight = parseFloat(row.weightElem.value);
            row.region.weight = !isNaN(weight) ? weight : 1;
            this.regionChanged.next(this.rows.indexOf(row));
        }

        private onDeleteClicked(row: TableRow): void {
            let index = this.rows.indexOf(row);
            if (index >= 0)
                this.removeRequested.next(index);
        }

        private createStylesheet(): HTMLStyleElement {
            let styleElem = document.createElement('style');
            styleElem.innerHTML = `
                .${PromptListControl.classNames.addButton} {
                    margin: 10px 30px !important;
                    align-self: start !important;
                }
                .${PromptListControl.classNames.table} {
                    width: 100%;
                    margin-bottom: 10px;
                }
                .${PromptListControl.classNames.table} input {
                    width: 100%;
                }
                .${PromptListControl.classNames.colorCell} {
                    width: 30px;
                    text-align: center;
                    position: relative;
                    cursor: pointer;
                }
                .${PromptListControl.classNames.colorMarker} {
                    width: 10px;
                    height: 10px;
                    border-radius: 5px;
                    border: 1px var(--input-border-color) solid;
                    position: absolute;
                    left: 50%;
                    top: 50%;
                    margin: -5px 0 0 -5px;
                }
                .${PromptListControl.classNames.weightCell} {
                    width: 70px;
                }
                .${PromptListControl.classNames.deleteCell} {
                    width: 30px;
                }
                .${PromptListControl.classNames.deleteCell} button {
                    visibility: hidden;
                }
                tr:hover .${PromptListControl.classNames.deleteCell} button {
                    visibility: visible;
                }
            `;
            return styleElem;
        }
    }
}
