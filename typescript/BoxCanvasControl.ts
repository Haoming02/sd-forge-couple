namespace ForgeCouple {
    interface Box {
        region: Region;
        fillElem: HTMLDivElement;
        borderElem: HTMLDivElement;
    }

    interface BorderSelection {
        left: boolean;
        top: boolean;
        right: boolean;
        bottom: boolean;
    }

    interface Point {
        clientX: number;
        clientY: number;
    }

    export class BoxCanvasControl {
        private static stylesheetCreated = false;
        private static readonly classNames = {
            wrapper:        'forge-couple--box-canvas--wrapper',
            canvas:         'forge-couple--box-canvas--empty-canvas',
            boxBorder:      'forge-couple--box-canvas--border',
            boxFill:        'forge-couple--box-canvas--fill',
            toolbar:        'forge-couple--box-canvas--toolbar',
            toolbarButton:  'forge-couple--box-canvas--toolbar-button'
        };
        private static readonly resizeHandleWidth = 20;
        private static readonly defaultZIndex = 1;
        private static readonly activeZIndex  = 2;

        private wrapperElem!: HTMLDivElement;
        private canvasElem!: HTMLDivElement;
        private imageElem?: HTMLImageElement;
        private imageLoadUrl?: string;
        private emptyAspectRatio = 1;
        private imageAspectRatio = 1;

        private toolbarElem!: HTMLDivElement;
        private clearImageToolbarButtonElem!: HTMLButtonElement;
        private imageInputElem!: HTMLInputElement;

        private boxes: Box[] = [];
        private activeBox?: Box;
        private dragStartMouse?: Point;
        private dragStartRect?: DOMRect;
        private dragBorders?: BorderSelection;

        constructor(containerElem: HTMLElement, private forImg2img: boolean) {
            if (!BoxCanvasControl.stylesheetCreated) {
                document.head.appendChild(this.createStylesheet());
                BoxCanvasControl.stylesheetCreated = true;
            }

            this.createCanvas(containerElem);
            this.createToolbar();
        }

        public setAspectRatio(aspectRatio: number): void {
            this.emptyAspectRatio = aspectRatio;
            this.updateCanvasSize();
        }

        public setRegions(regions: Region[]): void {
            for (let i = 0; i < regions.length; i++) {
                let box: Box;
                if (i < this.boxes.length) {
                    box = this.boxes[i];
                    box.region = regions[i];
                } else {
                    box = this.addBox(regions[i]);
                }
                this.updateBox(box);
            }

            while (this.boxes.length > regions.length) {
                this.removeRegion(this.boxes.length - 1);
            }
        }

        public addRegion(region: Region): void {
            this.addBox(region);
        }

        public selectRegion(index: number): void {
            this.bringToFront(this.boxes[index]);
        }

        public updateRegion(index: number): void {
            this.updateBox(this.boxes[index]);
        }

        public removeRegion(index: number): void {
            let box = this.boxes.splice(index, 1)[0];
            box.fillElem.parentElement?.removeChild(box.fillElem);
            box.borderElem.parentElement?.removeChild(box.borderElem);
        }

        public regionSelected = new Subject<number>();
        public regionChanged = new Subject<number>();

        private createCanvas(containerElem: HTMLElement): void {
            this.wrapperElem = document.createElement('div');
            this.wrapperElem.className = BoxCanvasControl.classNames.wrapper;
            containerElem.appendChild(this.wrapperElem);

            this.canvasElem = document.createElement('div');
            this.canvasElem.className = BoxCanvasControl.classNames.canvas;
            this.canvasElem.addEventListener('dragover', e => this.onCanvasDragOver(e));
            this.canvasElem.addEventListener('drop', e => this.onCanvasDrop(e));
            this.canvasElem.addEventListener('mouseover',  e => this.onCanvasMouseOver(e));
            this.canvasElem.addEventListener('mousemove',  e => this.onCanvasMouseMove(e));
            this.canvasElem.addEventListener('mouseleave', e => this.onCanvasMouseLeave(e));
            this.canvasElem.addEventListener('mousedown',  e => this.onCanvasMouseDown(e));
            this.wrapperElem.appendChild(this.canvasElem);
        }

        private updateCanvasSize(): void {
            let aspectRatio = this.imageElem ? this.imageAspectRatio : this.emptyAspectRatio;
            this.canvasElem.style.paddingBottom = `${1 / aspectRatio * 100}%`;
        }

        private createToolbar(): void {
            this.toolbarElem = document.createElement('div');
            this.toolbarElem.className = BoxCanvasControl.classNames.toolbar;
            this.addToolbarButton('📂', 'Open background image...', () => this.onOpenImageClicked());
            
            if (this.forImg2img) {
                let loadInputImageButtonElem = this.addToolbarButton('🖼️', 'Use img2img image as background', () => this.onLoadImg2imgClicked());
                loadInputImageButtonElem.disabled = !WebUI.isInputImageLoaded();
                WebUI.getInputImageLoadedSubject()?.subscribe(loaded => loadInputImageButtonElem.disabled = !loaded);
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

        private addToolbarButton(icon: string, title: string, callback: () => void): HTMLButtonElement {
            let toolbarButtonElem = WebUI.createButton(icon);
            toolbarButtonElem.className += ' ' + BoxCanvasControl.classNames.toolbarButton;
            toolbarButtonElem.innerText = icon;
            toolbarButtonElem.title = title;
            toolbarButtonElem.addEventListener('click', callback);
            this.toolbarElem.appendChild(toolbarButtonElem);
            return toolbarButtonElem;
        }

        private onOpenImageClicked(): void {
            if (this.imageLoadUrl)
                return;

            this.imageInputElem.click();
        }

        private onImageFileSelected(): void {
            if (!this.imageInputElem.files?.length)
                return;

            this.loadImageFromUrl(URL.createObjectURL(this.imageInputElem.files[0]));
        }

        private onLoadImg2imgClicked(): void {
            let url = WebUI.getInputImageUrl();
            if (url)
                this.loadImageFromUrl(url);
        }
        
        private onCanvasDragOver(event: DragEvent): void {
            event.preventDefault();
            event.stopPropagation();
        }

        private onCanvasDrop(event: DragEvent): void {
            if (!event.dataTransfer?.files?.length)
                return;

            event.preventDefault();
            this.loadImageFromUrl(URL.createObjectURL(event.dataTransfer.files[0]));
        }

        private loadImageFromUrl(url: string): void {
            if (this.imageLoadUrl)
                return;

            this.onClearImageClicked();

            this.imageLoadUrl = url;
            this.imageElem = document.createElement('img');
            this.imageElem.addEventListener('load', () => this.onImageLoaded(), { once: true });
            this.imageElem.src = this.imageLoadUrl;
        }

        private onImageLoaded(): void {
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

        private onClearImageClicked(): void {
            if (!this.imageElem || this.imageLoadUrl)
                return;

            this.canvasElem.removeChild(this.imageElem);
            this.imageElem = undefined;
            this.updateCanvasSize();

            this.clearImageToolbarButtonElem.disabled = true;
        }

        private addBox(region: Region): Box {
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

        private updateBox(box: Box): void {
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
                elem.style.left   = `${box.region.x      * 100}%`;
                elem.style.top    = `${box.region.y      * 100}%`;
                elem.style.width  = `${box.region.width  * 100}%`;
                elem.style.height = `${box.region.height * 100}%`;
            }
        }

        private onCanvasMouseOver(event: MouseEvent): void {
            if (this.dragBorders)
                return;

            this.activeBox = this.boxes.find(b => b.borderElem === event.target);
        }

        private onCanvasMouseMove(event: MouseEvent): void {
            if (this.dragBorders || !this.activeBox)
                return;

            let selection = this.getBordersToDrag(event);
            if (!selection)
                return;

            let borderElem = this.activeBox.borderElem;
            if (selection.left && selection.top && selection.right && selection.bottom) {
                borderElem.style.cursor = 'move';
            } else if (selection.left && selection.top || selection.right && selection.bottom) {
                borderElem.style.cursor = 'nw-resize';
            } else if (selection.left && selection.bottom || selection.right && selection.top) {
                borderElem.style.cursor = 'ne-resize';
            } else if (selection.left || selection.right) {
                borderElem.style.cursor = 'ew-resize';
            } else if (selection.top || selection.bottom) {
                borderElem.style.cursor = 'ns-resize';
            } else {
                borderElem.style.cursor = 'default';
            }
        }

        private onCanvasMouseLeave(event: MouseEvent): void {
            if (this.dragBorders)
                return;

            this.activeBox = undefined;
        }

        private onCanvasMouseDown(event: MouseEvent): void {
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

        private onPageMouseMove = (event: MouseEvent): void => {
            if (!this.activeBox || !this.dragStartMouse || !this.dragStartRect || !this.dragBorders)
                return;

            let containerRect = this.canvasElem.getBoundingClientRect();
            let xOffset = event.clientX - this.dragStartMouse.clientX;
            let yOffset = event.clientY - this.dragStartMouse.clientY;

            let left = this.clamp(
                this.dragStartRect.left + (this.dragBorders.left ? xOffset : 0),
                containerRect.left,
                this.dragBorders.right ? containerRect.right - this.dragStartRect.width : this.dragStartRect.right - BoxCanvasControl.resizeHandleWidth * 2
            );
            let top = this.clamp(
                this.dragStartRect.top + (this.dragBorders.top ? yOffset : 0),
                containerRect.top,
                this.dragBorders.bottom ? containerRect.bottom - this.dragStartRect.height : this.dragStartRect.bottom - BoxCanvasControl.resizeHandleWidth * 2
            );
            let right = this.clamp(
                this.dragStartRect.right + (this.dragBorders.right ? xOffset : 0),
                this.dragBorders.left ? containerRect.left + this.dragStartRect.width : this.dragStartRect.left + BoxCanvasControl.resizeHandleWidth * 2,
                containerRect.right
            );
            let bottom = this.clamp(
                this.dragStartRect.bottom + (this.dragBorders.bottom ? yOffset : 0),
                this.dragBorders.top ? containerRect.top + this.dragStartRect.height : this.dragStartRect.top + BoxCanvasControl.resizeHandleWidth * 2,
                containerRect.bottom
            );

            this.activeBox.region.setClientRect(
                this.canvasElem.getBoundingClientRect(),
                new DOMRect(left, top, right - left, bottom - top)
            );
            this.updateBox(this.activeBox);
        }

        private onPageMouseUp = (event: MouseEvent): void => {
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
        }

        private bringToFront(frontBox: Box): void {
            for (let box of this.boxes) {
                let zIndex = (box === frontBox ? BoxCanvasControl.activeZIndex : BoxCanvasControl.defaultZIndex).toString();
                box.fillElem.style.zIndex = zIndex;
                box.borderElem.style.zIndex = zIndex;
            }
        }

        private getBordersToDrag(mouse: Point): BorderSelection | null {
            if (!this.activeBox)
                return null;

            let rect = this.activeBox.borderElem.getBoundingClientRect();
            let selection: BorderSelection = {
                left:   mouse.clientX <  rect.left   + BoxCanvasControl.resizeHandleWidth,
                top:    mouse.clientY <  rect.top    + BoxCanvasControl.resizeHandleWidth,
                right:  mouse.clientX >= rect.right  - BoxCanvasControl.resizeHandleWidth,
                bottom: mouse.clientY >= rect.bottom - BoxCanvasControl.resizeHandleWidth,
            };
            if (!selection.left && !selection.top && !selection.right && !selection.bottom) {
                selection.left   = true;
                selection.top    = true;
                selection.right  = true;
                selection.bottom = true;
            }
            return selection;
        }

        private createStylesheet(): HTMLStyleElement {
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

        private clamp(value: number, min: number, max: number): number {
            return Math.min(Math.max(value, min), max);
        }
    }
}
