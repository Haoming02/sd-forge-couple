"use strict";
var ForgeCouple;
(function (ForgeCouple) {
    class BoxCanvasControl {
        forImg2img;
        static stylesheetCreated = false;
        static classNames = {
            wrapper: 'forge-couple--box-canvas--wrapper',
            canvas: 'forge-couple--box-canvas--empty-canvas',
            boxBorder: 'forge-couple--box-canvas--border',
            boxFill: 'forge-couple--box-canvas--fill',
            toolbar: 'forge-couple--box-canvas--toolbar',
            toolbarButton: 'forge-couple--box-canvas--toolbar-button'
        };
        static resizeHandleWidth = 20;
        static defaultZIndex = 1;
        static activeZIndex = 2;
        wrapperElem;
        canvasElem;
        imageElem;
        imageLoadUrl;
        emptyAspectRatio = 1;
        imageAspectRatio = 1;
        toolbarElem;
        clearImageToolbarButtonElem;
        imageInputElem;
        boxes = [];
        activeBox;
        dragStartMouse;
        dragStartRect;
        dragBorders;
        constructor(containerElem, forImg2img) {
            this.forImg2img = forImg2img;
            if (!BoxCanvasControl.stylesheetCreated) {
                document.head.appendChild(this.createStylesheet());
                BoxCanvasControl.stylesheetCreated = true;
            }
            this.createCanvas(containerElem);
            this.createToolbar();
        }
        setAspectRatio(aspectRatio) {
            this.emptyAspectRatio = aspectRatio;
            this.updateCanvasSize();
        }
        setRegions(regions) {
            for (let i = 0; i < regions.length; i++) {
                let box;
                if (i < this.boxes.length) {
                    box = this.boxes[i];
                    box.region = regions[i];
                }
                else {
                    box = this.addBox(regions[i]);
                }
                this.updateBox(box);
            }
            while (this.boxes.length > regions.length) {
                this.removeRegion(this.boxes.length - 1);
            }
        }
        addRegion(region) {
            this.addBox(region);
        }
        selectRegion(index) {
            this.bringToFront(this.boxes[index]);
        }
        updateRegion(index) {
            this.updateBox(this.boxes[index]);
        }
        removeRegion(index) {
            let box = this.boxes.splice(index, 1)[0];
            box.fillElem.parentElement?.removeChild(box.fillElem);
            box.borderElem.parentElement?.removeChild(box.borderElem);
        }
        regionSelected = new ForgeCouple.Subject();
        regionChanged = new ForgeCouple.Subject();
        createCanvas(containerElem) {
            this.wrapperElem = document.createElement('div');
            this.wrapperElem.className = BoxCanvasControl.classNames.wrapper;
            containerElem.appendChild(this.wrapperElem);
            this.canvasElem = document.createElement('div');
            this.canvasElem.className = BoxCanvasControl.classNames.canvas;
            this.canvasElem.addEventListener('dragover', e => this.onCanvasDragOver(e));
            this.canvasElem.addEventListener('drop', e => this.onCanvasDrop(e));
            this.canvasElem.addEventListener('mouseover', e => this.onCanvasMouseOver(e));
            this.canvasElem.addEventListener('mousemove', e => this.onCanvasMouseMove(e));
            this.canvasElem.addEventListener('mouseleave', e => this.onCanvasMouseLeave(e));
            this.canvasElem.addEventListener('mousedown', e => this.onCanvasMouseDown(e));
            this.wrapperElem.appendChild(this.canvasElem);
        }
        updateCanvasSize() {
            let aspectRatio = this.imageElem ? this.imageAspectRatio : this.emptyAspectRatio;
            this.canvasElem.style.paddingBottom = `${1 / aspectRatio * 100}%`;
        }
        createToolbar() {
            this.toolbarElem = document.createElement('div');
            this.toolbarElem.className = BoxCanvasControl.classNames.toolbar;
            this.addToolbarButton('📂', 'Open background image...', () => this.onOpenImageClicked());
            if (this.forImg2img) {
                let loadInputImageButtonElem = this.addToolbarButton('🖼️', 'Use img2img image as background', () => this.onLoadImg2imgClicked());
                loadInputImageButtonElem.disabled = !ForgeCouple.WebUI.isInputImageLoaded();
                ForgeCouple.WebUI.getInputImageLoadedSubject()?.subscribe(loaded => loadInputImageButtonElem.disabled = !loaded);
            }
            this.clearImageToolbarButtonElem = this.addToolbarButton('❌', 'Clear background image', () => this.onClearImageClicked());
            this.clearImageToolbarButtonElem.disabled = true;
            this.wrapperElem.appendChild(this.toolbarElem);
            this.imageInputElem = document.createElement('input');
            this.imageInputElem.type = 'file';
            this.imageInputElem.style.display = 'none';
            this.imageInputElem.addEventListener('change', () => this.onImageFileSelected());
            this.wrapperElem.appendChild(this.imageInputElem);
        }
        addToolbarButton(icon, title, callback) {
            let toolbarButtonElem = ForgeCouple.WebUI.createButton(icon);
            toolbarButtonElem.className += ' ' + BoxCanvasControl.classNames.toolbarButton;
            toolbarButtonElem.innerText = icon;
            toolbarButtonElem.title = title;
            toolbarButtonElem.addEventListener('click', callback);
            this.toolbarElem.appendChild(toolbarButtonElem);
            return toolbarButtonElem;
        }
        onOpenImageClicked() {
            if (this.imageLoadUrl)
                return;
            this.imageInputElem.click();
        }
        onImageFileSelected() {
            if (!this.imageInputElem.files?.length)
                return;
            this.loadImageFromUrl(URL.createObjectURL(this.imageInputElem.files[0]));
        }
        onLoadImg2imgClicked() {
            let url = ForgeCouple.WebUI.getInputImageUrl();
            if (url)
                this.loadImageFromUrl(url);
        }
        onCanvasDragOver(event) {
            event.preventDefault();
            event.stopPropagation();
        }
        onCanvasDrop(event) {
            if (!event.dataTransfer?.files?.length)
                return;
            event.preventDefault();
            this.loadImageFromUrl(URL.createObjectURL(event.dataTransfer.files[0]));
        }
        loadImageFromUrl(url) {
            if (this.imageLoadUrl)
                return;
            this.onClearImageClicked();
            this.imageLoadUrl = url;
            this.imageElem = document.createElement('img');
            this.imageElem.addEventListener('load', () => this.onImageLoaded(), { once: true });
            this.imageElem.src = this.imageLoadUrl;
        }
        onImageLoaded() {
            if (!this.imageLoadUrl || !this.imageElem)
                return;
            if (this.imageLoadUrl.startsWith('blob:'))
                URL.revokeObjectURL(this.imageLoadUrl);
            this.imageLoadUrl = undefined;
            this.imageAspectRatio = this.imageElem.naturalWidth / this.imageElem.naturalHeight;
            this.updateCanvasSize();
            this.canvasElem.appendChild(this.imageElem);
            this.clearImageToolbarButtonElem.disabled = false;
        }
        onClearImageClicked() {
            if (!this.imageElem || this.imageLoadUrl)
                return;
            this.canvasElem.removeChild(this.imageElem);
            this.imageElem = undefined;
            this.updateCanvasSize();
            this.clearImageToolbarButtonElem.disabled = true;
        }
        addBox(region) {
            let fillElem = document.createElement('div');
            fillElem.className = BoxCanvasControl.classNames.boxFill;
            let borderElem = document.createElement('div');
            borderElem.className = BoxCanvasControl.classNames.boxBorder;
            let box = { region, fillElem, borderElem };
            this.boxes.push(box);
            this.updateBox(box);
            this.bringToFront(box);
            this.canvasElem.appendChild(fillElem);
            this.canvasElem.appendChild(borderElem);
            return box;
        }
        updateBox(box) {
            if (!box.region.enabled) {
                for (let elem of [box.fillElem, box.borderElem]) {
                    elem.style.visibility = 'hidden';
                }
                return;
            }
            box.fillElem.style.backgroundColor = box.region.color;
            box.borderElem.style.borderColor = box.region.color;
            box.borderElem.style.color = box.region.color;
            box.borderElem.innerText = box.region.prompt;
            for (let elem of [box.fillElem, box.borderElem]) {
                elem.style.visibility = 'visible';
                elem.style.left = `${box.region.x * 100}%`;
                elem.style.top = `${box.region.y * 100}%`;
                elem.style.width = `${box.region.width * 100}%`;
                elem.style.height = `${box.region.height * 100}%`;
            }
        }
        onCanvasMouseOver(event) {
            if (this.dragBorders)
                return;
            this.activeBox = this.boxes.find(b => b.borderElem === event.target);
        }
        onCanvasMouseMove(event) {
            if (this.dragBorders || !this.activeBox)
                return;
            let selection = this.getBordersToDrag(event);
            if (!selection)
                return;
            let borderElem = this.activeBox.borderElem;
            if (selection.left && selection.top && selection.right && selection.bottom) {
                borderElem.style.cursor = 'move';
            }
            else if (selection.left && selection.top || selection.right && selection.bottom) {
                borderElem.style.cursor = 'nw-resize';
            }
            else if (selection.left && selection.bottom || selection.right && selection.top) {
                borderElem.style.cursor = 'ne-resize';
            }
            else if (selection.left || selection.right) {
                borderElem.style.cursor = 'ew-resize';
            }
            else if (selection.top || selection.bottom) {
                borderElem.style.cursor = 'ns-resize';
            }
            else {
                borderElem.style.cursor = 'default';
            }
        }
        onCanvasMouseLeave(event) {
            if (this.dragBorders)
                return;
            this.activeBox = undefined;
        }
        onCanvasMouseDown(event) {
            if (event.button != 0 || !this.activeBox)
                return;
            let borders = this.getBordersToDrag(event);
            if (!borders)
                return;
            this.bringToFront(this.activeBox);
            this.dragStartMouse = { clientX: event.clientX, clientY: event.clientY };
            this.dragStartRect = this.activeBox.region.getClientRect(this.canvasElem.getBoundingClientRect());
            this.dragBorders = borders;
            document.body.addEventListener('mousemove', this.onPageMouseMove);
            document.body.addEventListener('mouseup', this.onPageMouseUp);
            event.preventDefault();
        }
        onPageMouseMove = (event) => {
            if (!this.activeBox || !this.dragStartMouse || !this.dragStartRect || !this.dragBorders)
                return;
            let containerRect = this.canvasElem.getBoundingClientRect();
            let xOffset = event.clientX - this.dragStartMouse.clientX;
            let yOffset = event.clientY - this.dragStartMouse.clientY;
            let left = this.clamp(this.dragStartRect.left + (this.dragBorders.left ? xOffset : 0), containerRect.left, this.dragBorders.right ? containerRect.right - this.dragStartRect.width : this.dragStartRect.right - BoxCanvasControl.resizeHandleWidth * 2);
            let top = this.clamp(this.dragStartRect.top + (this.dragBorders.top ? yOffset : 0), containerRect.top, this.dragBorders.bottom ? containerRect.bottom - this.dragStartRect.height : this.dragStartRect.bottom - BoxCanvasControl.resizeHandleWidth * 2);
            let right = this.clamp(this.dragStartRect.right + (this.dragBorders.right ? xOffset : 0), this.dragBorders.left ? containerRect.left + this.dragStartRect.width : this.dragStartRect.left + BoxCanvasControl.resizeHandleWidth * 2, containerRect.right);
            let bottom = this.clamp(this.dragStartRect.bottom + (this.dragBorders.bottom ? yOffset : 0), this.dragBorders.top ? containerRect.top + this.dragStartRect.height : this.dragStartRect.top + BoxCanvasControl.resizeHandleWidth * 2, containerRect.bottom);
            this.activeBox.region.setClientRect(this.canvasElem.getBoundingClientRect(), new DOMRect(left, top, right - left, bottom - top));
            this.updateBox(this.activeBox);
        };
        onPageMouseUp = (event) => {
            if (event.button != 0)
                return;
            this.dragStartMouse = undefined;
            this.dragStartRect = undefined;
            this.dragBorders = undefined;
            document.body.removeEventListener('mousemove', this.onPageMouseMove);
            document.body.removeEventListener('mouseup', this.onPageMouseUp);
            if (this.activeBox) {
                let index = this.boxes.indexOf(this.activeBox);
                if (index >= 0) {
                    this.regionSelected.next(index);
                    this.regionChanged.next(index);
                }
            }
        };
        bringToFront(frontBox) {
            for (let box of this.boxes) {
                let zIndex = (box === frontBox ? BoxCanvasControl.activeZIndex : BoxCanvasControl.defaultZIndex).toString();
                box.fillElem.style.zIndex = zIndex;
                box.borderElem.style.zIndex = zIndex;
            }
        }
        getBordersToDrag(mouse) {
            if (!this.activeBox)
                return null;
            let rect = this.activeBox.borderElem.getBoundingClientRect();
            let selection = {
                left: mouse.clientX < rect.left + BoxCanvasControl.resizeHandleWidth,
                top: mouse.clientY < rect.top + BoxCanvasControl.resizeHandleWidth,
                right: mouse.clientX >= rect.right - BoxCanvasControl.resizeHandleWidth,
                bottom: mouse.clientY >= rect.bottom - BoxCanvasControl.resizeHandleWidth,
            };
            if (!selection.left && !selection.top && !selection.right && !selection.bottom) {
                selection.left = true;
                selection.top = true;
                selection.right = true;
                selection.bottom = true;
            }
            return selection;
        }
        createStylesheet() {
            let styleElem = document.createElement('style');
            styleElem.innerHTML = `
                .${BoxCanvasControl.classNames.wrapper} {
                    width: 80%;
                    margin: 0 auto;
                    position: relative;
                }
                .${BoxCanvasControl.classNames.canvas} {
                    background-color: black;
                    position: relative;
                }
                .${BoxCanvasControl.classNames.canvas} img {
                    position: absolute;
                    left: 0;
                    top: 0;
                    width: 100%;
                }
                .${BoxCanvasControl.classNames.toolbar} {
                    position: absolute;
                    top: 0;
                    right: -36px;
                    width: 32px;
                }
                .${BoxCanvasControl.classNames.toolbarButton} {
                    width: 32px !important;
                    height: 32px !important;
                    padding: 0 !important;
                    margin-bottom: 4px !important;
                }
                .${BoxCanvasControl.classNames.boxFill} {
                    position: absolute;
                    opacity: 0.3;
                    box-sizing: border-box;
                }
                .${BoxCanvasControl.classNames.boxBorder} {
                    position: absolute;
                    border-style: solid;
                    border-width: 2px;
                    box-sizing: border-box;
                    padding: 4px;
                    overflow: hidden;
                }
            `;
            return styleElem;
        }
        clamp(value, min, max) {
            return Math.min(Math.max(value, min), max);
        }
    }
    ForgeCouple.BoxCanvasControl = BoxCanvasControl;
})(ForgeCouple || (ForgeCouple = {}));
var ForgeCouple;
(function (ForgeCouple) {
    class CustomRegionControl {
        regionsInputElem;
        forImg2img;
        static colors = ['red', 'orange', 'yellow', 'green', 'blue', 'violet', 'purple', 'white'];
        static instances = new Map();
        static refreshTxt2img() {
            CustomRegionControl.refresh(false);
        }
        static refreshImg2img() {
            CustomRegionControl.refresh(true);
        }
        static refresh(forImg2img) {
            let instance = this.instances.get(forImg2img);
            if (!instance) {
                let suffix = forImg2img ? 'img2img' : 'txt2img';
                let groupElem = document.querySelector(`#forge-couple--adv-group-${suffix}`);
                let regionsInputElem = document.querySelector(`#forge-couple--adv-regions-${suffix} textarea`);
                if (!groupElem || !regionsInputElem)
                    return;
                instance = new CustomRegionControl(groupElem, regionsInputElem, forImg2img);
                this.instances.set(forImg2img, instance);
            }
            instance.onImageSizeChanged();
            instance.refreshRegions();
        }
        regions = [];
        promptPresenter;
        boxPresenter;
        sendingToGradio = false;
        constructor(containerElem, regionsInputElem, forImg2img) {
            this.regionsInputElem = regionsInputElem;
            this.forImg2img = forImg2img;
            this.promptPresenter = new ForgeCouple.PromptListControl(containerElem, CustomRegionControl.colors.length);
            this.boxPresenter = new ForgeCouple.BoxCanvasControl(containerElem, forImg2img);
            ForgeCouple.WebUI.getOutputImageSizeSubject(forImg2img)?.subscribe(_ => this.onImageSizeChanged());
            this.promptPresenter.addRequested.subscribe(() => this.addRegion());
            this.promptPresenter.regionSelected.subscribe(index => this.boxPresenter.selectRegion(index));
            this.promptPresenter.regionChanged.subscribe(index => this.onPromptChanged(index));
            this.promptPresenter.removeRequested.subscribe(index => this.removeRegion(index));
            this.boxPresenter.regionSelected.subscribe(index => this.promptPresenter.selectRegion(index));
            this.boxPresenter.regionChanged.subscribe(_ => this.sendRegionsToGradio());
            this.addRegion();
        }
        refreshRegions() {
            if (this.sendingToGradio) {
                this.sendingToGradio = false;
                return;
            }
            let regions = this.regionsInputElem.value.split('\n').filter(l => l.trim().length > 0).map(ForgeCouple.Region.deserialize);
            while (regions.length > CustomRegionControl.colors.length) {
                regions.pop();
            }
            for (let i = 0; i < regions.length; i++) {
                regions[i].color = CustomRegionControl.colors[i];
            }
            this.regions = regions;
            this.promptPresenter.setRegions(regions);
            this.boxPresenter.setRegions(regions);
        }
        onImageSizeChanged() {
            let size = ForgeCouple.WebUI.getOutputImageSize(this.forImg2img) ?? { width: 512, height: 512 };
            let aspect = size.height > 0 ? size.width / size.height : 1;
            this.boxPresenter.setAspectRatio(aspect);
        }
        addRegion() {
            if (this.regions.length >= CustomRegionControl.colors.length)
                return;
            let region = new ForgeCouple.Region();
            for (let color of CustomRegionControl.colors) {
                if (!this.regions.some(r => r.color === color)) {
                    region.color = color;
                    break;
                }
            }
            this.regions.push(region);
            this.promptPresenter.addRegion(region);
            this.boxPresenter.addRegion(region);
            this.sendRegionsToGradio();
        }
        onPromptChanged(index) {
            this.boxPresenter.updateRegion(index);
            this.sendRegionsToGradio();
        }
        removeRegion(index) {
            this.regions.splice(index, 1);
            this.promptPresenter.removeRegion(index);
            this.boxPresenter.removeRegion(index);
            this.sendRegionsToGradio();
        }
        sendRegionsToGradio() {
            let serializedRegions = this.regions.map(r => r.serialize()).join('\n');
            if (serializedRegions === this.regionsInputElem.value)
                return;
            this.sendingToGradio = true;
            this.regionsInputElem.value = serializedRegions;
            this.regionsInputElem.dispatchEvent(new Event('input'));
        }
    }
    ForgeCouple.CustomRegionControl = CustomRegionControl;
})(ForgeCouple || (ForgeCouple = {}));
var ForgeCouple;
(function (ForgeCouple) {
    class PromptListControl {
        maxRegions;
        static stylesheetCreated = false;
        static classNames = {
            addButton: 'forge-couple--prompt-list--add-button',
            table: 'forge-couple--prompt-list--table',
            colorCell: 'forge-couple--prompt-list--color-cell',
            colorMarker: 'forge-couple--prompt-list--color-marker',
            promptCell: 'forge-couple--prompt-list--prompt-cell',
            weightCell: 'forge-couple--prompt-list--weight-cell',
            deleteCell: 'forge-couple--prompt-list--delete-cell'
        };
        addButtonElem;
        tableElem;
        rows = [];
        constructor(containerElem, maxRegions) {
            this.maxRegions = maxRegions;
            if (!PromptListControl.stylesheetCreated) {
                document.head.appendChild(this.createStylesheet());
                PromptListControl.stylesheetCreated = true;
            }
            this.addButtonElem = ForgeCouple.WebUI.createButton('Add region');
            this.addButtonElem.className += ' ' + PromptListControl.classNames.addButton;
            this.addButtonElem.addEventListener('click', _ => this.addRequested.next());
            containerElem.appendChild(this.addButtonElem);
            this.tableElem = document.createElement('table');
            this.tableElem.className = PromptListControl.classNames.table;
            containerElem.appendChild(this.tableElem);
        }
        setRegions(regions) {
            for (let i = 0; i < regions.length; i++) {
                let row;
                if (i < this.rows.length) {
                    row = this.rows[i];
                    row.region = regions[i];
                }
                else {
                    row = this.addGridRow(regions[i]);
                }
                this.updateTableRow(row);
            }
            while (this.rows.length > regions.length) {
                this.removeRegion(this.rows.length - 1);
            }
            this.updateAddButton();
        }
        addRegion(region) {
            this.addGridRow(region);
            this.updateAddButton();
            this.selectRegion(this.rows.length - 1);
        }
        selectRegion(index) {
            let row = this.rows[index];
            if (document.activeElement == row.promptElem)
                this.onPromptUpdated(row);
            else
                row.promptElem.focus();
        }
        removeRegion(index) {
            let row = this.rows.splice(index, 1)[0];
            row.rowElem.parentElement?.removeChild(row.rowElem);
            this.updateAddButton();
        }
        addRequested = new ForgeCouple.Subject();
        regionSelected = new ForgeCouple.Subject();
        regionChanged = new ForgeCouple.Subject();
        removeRequested = new ForgeCouple.Subject();
        addGridRow(region) {
            let rowElem = document.createElement('tr');
            rowElem.innerHTML = `
                <td class="${PromptListControl.classNames.colorCell}">
                    <div class="${PromptListControl.classNames.colorMarker}">
                    </div>
                </td>
                <td class="${PromptListControl.classNames.promptCell}">
                    <label class="${ForgeCouple.WebUI.inputClasses} container">
                        <input class="${ForgeCouple.WebUI.inputClasses}" placeholder="Prompt"/>
                    </label>
                </td>
                <td class="${PromptListControl.classNames.weightCell}">
                    <label class="${ForgeCouple.WebUI.inputClasses} container">
                        <input class="${ForgeCouple.WebUI.inputClasses}" placeholder="Weight"/>
                    </label>
                </td>
                <td class="${PromptListControl.classNames.deleteCell}">
                    <button class="${ForgeCouple.WebUI.buttonClasses}">❌</button>
                </td>
            `;
            let colorCell = rowElem.querySelector(`.${PromptListControl.classNames.colorCell}`);
            let colorElem = rowElem.querySelector(`.${PromptListControl.classNames.colorMarker}`);
            let promptElem = rowElem.querySelector(`.${PromptListControl.classNames.promptCell} input`);
            let weightElem = rowElem.querySelector(`.${PromptListControl.classNames.weightCell} input`);
            let deleteButtonElem = rowElem.querySelector(`.${PromptListControl.classNames.deleteCell} button`);
            if (!colorCell || !colorElem || !promptElem || !weightElem || !deleteButtonElem) {
                throw new Error('Forge Couple: Failed to create prompt row');
            }
            let row = { region, rowElem, colorElem, promptElem, weightElem, deleteButtonElem };
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
        updateTableRow(row) {
            row.colorElem.style.backgroundColor = row.region.enabled ? row.region.color : 'transparent';
            row.promptElem.value = row.region.prompt;
            row.weightElem.value = row.region.weight.toString();
        }
        updateAddButton() {
            this.addButtonElem.disabled = this.rows.length >= this.maxRegions;
        }
        onMarkerClicked(row) {
            row.region.enabled = !row.region.enabled;
            this.updateTableRow(row);
            this.regionChanged.next(this.rows.indexOf(row));
        }
        onPromptFocused(row) {
            this.regionSelected.next(this.rows.indexOf(row));
        }
        onPromptUpdated(row) {
            row.region.prompt = row.promptElem.value;
            this.regionChanged.next(this.rows.indexOf(row));
        }
        onWeightUpdated(row) {
            let weight = parseFloat(row.weightElem.value);
            row.region.weight = !isNaN(weight) ? weight : 1;
            this.regionChanged.next(this.rows.indexOf(row));
        }
        onDeleteClicked(row) {
            let index = this.rows.indexOf(row);
            if (index >= 0)
                this.removeRequested.next(index);
        }
        createStylesheet() {
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
    ForgeCouple.PromptListControl = PromptListControl;
})(ForgeCouple || (ForgeCouple = {}));
var ForgeCouple;
(function (ForgeCouple) {
    class Region {
        enabled = true;
        color = '';
        x = 0.4;
        y = 0.4;
        width = 0.2;
        height = 0.2;
        prompt = '';
        weight = 1;
        getClientRect(containerRect) {
            return new DOMRect(containerRect.left + this.x * containerRect.width, containerRect.top + this.y * containerRect.height, this.width * containerRect.width, this.height * containerRect.height);
        }
        setClientRect(containerRect, regionRect) {
            this.x = (regionRect.left - containerRect.left) / containerRect.width;
            this.y = (regionRect.top - containerRect.top) / containerRect.height;
            this.width = regionRect.width / containerRect.width;
            this.height = regionRect.height / containerRect.height;
        }
        serialize() {
            const prec = 5;
            return `${this.enabled ? 1 : 0},${this.x.toFixed(prec)},${this.y.toFixed(prec)},${this.width.toFixed(prec)},${this.height.toFixed(prec)},${this.weight},${this.prompt}`;
        }
        static deserialize(data) {
            let region = new Region();
            let parts = data.split(',');
            region.enabled = parseInt(parts.shift() ?? '1') != 0;
            region.x = parseFloat(parts.shift() ?? '0');
            region.y = parseFloat(parts.shift() ?? '0');
            region.width = parseFloat(parts.shift() ?? '1');
            region.height = parseFloat(parts.shift() ?? '1');
            region.weight = parseFloat(parts.shift() ?? '1');
            region.prompt = parts.join(',');
            return region;
        }
    }
    ForgeCouple.Region = Region;
})(ForgeCouple || (ForgeCouple = {}));
var ForgeCouple;
(function (ForgeCouple) {
    class Subject {
        listeners = [];
        subscribe(listener) {
            this.listeners.push(listener);
        }
        unsubscribe(listener) {
            let index = this.listeners.indexOf(listener);
            if (index >= 0)
                this.listeners.splice(index, 1);
        }
        next(arg) {
            for (let listener of this.listeners) {
                listener(arg);
            }
        }
    }
    ForgeCouple.Subject = Subject;
})(ForgeCouple || (ForgeCouple = {}));
var ForgeCouple;
(function (ForgeCouple) {
    class WebUI {
        static outputImageSizeFields = new Map();
        static outputImageSizeSubjects = new Map();
        static inputImageLoadedSubject = null;
        static resizeByTab = null;
        static svelteInputClass;
        static svelteButtonClass;
        static getOutputImageSize(forImg2img) {
            let inputs = WebUI.getOutputImageSizeFields(forImg2img);
            if (!inputs)
                return null;
            if (forImg2img) {
                let resizeByTab = WebUI.getResizeByTab();
                let resolutionPreview = WebUI.getResizeByResolutionPreview();
                if (resizeByTab?.style.display == 'block' && resolutionPreview) {
                    let resolution = resolutionPreview.innerText.match(/^(\d+)x(\d+)$/);
                    if (resolution)
                        return { width: parseInt(resolution[1]), height: parseInt(resolution[2]) };
                }
            }
            let width = parseInt(inputs.widthTextbox.value);
            let height = parseInt(inputs.heightTextbox.value);
            if (isNaN(width) || isNaN(height))
                return null;
            return { width, height };
        }
        static getOutputImageSizeSubject(forImg2img) {
            let subject = WebUI.outputImageSizeSubjects.get(forImg2img);
            if (!subject) {
                let inputs = WebUI.getOutputImageSizeFields(forImg2img);
                if (!inputs)
                    return null;
                let newSubject = new ForgeCouple.Subject();
                for (let input of Object.values(inputs)) {
                    input.addEventListener('change', () => WebUI.onOutputImageSizeChanged(forImg2img));
                }
                if (forImg2img) {
                    let resizeByTab = WebUI.getResizeByTab();
                    if (resizeByTab)
                        new MutationObserver(() => WebUI.onOutputImageSizeChanged(true)).observe(resizeByTab, { attributes: true, childList: true, subtree: true });
                }
                subject = newSubject;
                WebUI.outputImageSizeSubjects.set(forImg2img, subject);
            }
            return subject;
        }
        static onOutputImageSizeChanged(forImg2img) {
            let size = WebUI.getOutputImageSize(forImg2img);
            if (size)
                WebUI.outputImageSizeSubjects.get(forImg2img)?.next(size);
        }
        static isInputImageLoaded() {
            return WebUI.getInputImage() != null;
        }
        static getInputImageLoadedSubject() {
            if (!WebUI.inputImageLoadedSubject) {
                let wrapper = document.getElementById('img2img_image');
                if (wrapper == null)
                    return null;
                WebUI.inputImageLoadedSubject = new ForgeCouple.Subject();
                new MutationObserver(() => WebUI.inputImageLoadedSubject?.next(WebUI.isInputImageLoaded())).observe(wrapper, { childList: true, subtree: true });
            }
            return WebUI.inputImageLoadedSubject;
        }
        static getInputImageUrl() {
            return WebUI.getInputImage()?.src ?? null;
        }
        static getInputImage() {
            return document.querySelector('#img2img_image img');
        }
        static getOutputImageSizeFields(img2img) {
            let inputs = WebUI.outputImageSizeFields.get(img2img);
            if (!inputs) {
                let prefix = img2img ? 'img2img' : 'txt2img';
                let widthTextbox = document.querySelector(`#${prefix}_width  input[type=number]`);
                let widthSlider = document.querySelector(`#${prefix}_width  input[type=range]`);
                let heightTextbox = document.querySelector(`#${prefix}_height input[type=number]`);
                let heightSlider = document.querySelector(`#${prefix}_height input[type=range]`);
                if (!widthTextbox || !widthSlider || !heightTextbox || !heightSlider)
                    return null;
                inputs = { widthTextbox, widthSlider, heightTextbox, heightSlider };
                WebUI.outputImageSizeFields.set(img2img, inputs);
            }
            return inputs;
        }
        static getResizeByTab() {
            return WebUI.resizeByTab ??= document.querySelector('#img2img_tab_resize_by');
        }
        static getResizeByResolutionPreview() {
            return document.querySelector('#img2img_scale_resolution_preview span[class=resolution]:nth-child(2)');
        }
        static createWrappedInput(placeholder) {
            let label = document.createElement('label');
            label.className = `${WebUI.inputClasses} container`;
            let input = document.createElement('input');
            input.className = WebUI.inputClasses;
            input.placeholder = placeholder;
            label.appendChild(input);
            return [label, input];
        }
        static createButton(text) {
            let button = document.createElement('button');
            button.className = WebUI.buttonClasses;
            button.innerText = text;
            button.style.minWidth = 'unset';
            button.style.maxWidth = 'unset';
            return button;
        }
        static get inputClasses() {
            WebUI.svelteInputClass ??= WebUI.getSvelteClassByTagName('textarea');
            return WebUI.svelteInputClass ?? '';
        }
        static get buttonClasses() {
            WebUI.svelteButtonClass ??= WebUI.getSvelteClassByTagName('button');
            return `lg secondary gradio-button tool absolute ${WebUI.svelteButtonClass}`;
        }
        static getSvelteClassByTagName(tagName) {
            let classNames = document.querySelector(tagName + '[class*="svelte-"]')?.className;
            if (!classNames)
                return '';
            return classNames.split(' ').find(c => c.startsWith('svelte-')) ?? '';
        }
    }
    ForgeCouple.WebUI = WebUI;
})(ForgeCouple || (ForgeCouple = {}));
//# sourceMappingURL=regions.js.map