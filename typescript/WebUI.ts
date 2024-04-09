namespace ForgeCouple {
    type ImageSizeFields = Record<'widthTextbox' | 'widthSlider' | 'heightTextbox' | 'heightSlider', HTMLInputElement>

    export interface ImageSize {
        width: number;
        height: number;
    }

    export class WebUI {
        private static outputImageSizeFields = new Map<boolean, ImageSizeFields>();
        private static outputImageSizeSubjects = new Map<boolean, Subject<ImageSize>>();
        
        private static inputImageLoadedSubject: Subject<boolean> | null = null;
        private static resizeByTab: HTMLDivElement | null = null;

        private static svelteInputClass?: string;
        private static svelteButtonClass?: string;

        public static getOutputImageSize(forImg2img: boolean): ImageSize | null {
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

        public static getOutputImageSizeSubject(forImg2img: boolean): Subject<ImageSize> | null {
            let subject = WebUI.outputImageSizeSubjects.get(forImg2img);
            if (!subject) {
                let inputs = WebUI.getOutputImageSizeFields(forImg2img);
                if (!inputs)
                    return null;

                let newSubject = new Subject<ImageSize>();
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

        private static onOutputImageSizeChanged(forImg2img: boolean): void {
            let size = WebUI.getOutputImageSize(forImg2img);
            if (size)
                WebUI.outputImageSizeSubjects.get(forImg2img)?.next(size);
        }

        public static isInputImageLoaded(): boolean {
            return WebUI.getInputImage() != null;
        }
        
        public static getInputImageLoadedSubject(): Subject<boolean> | null {
            if (!WebUI.inputImageLoadedSubject) {
                let wrapper = document.getElementById('img2img_image');
                if (wrapper == null)
                    return null;

                WebUI.inputImageLoadedSubject = new Subject<boolean>();
                new MutationObserver(
                    () => WebUI.inputImageLoadedSubject?.next(WebUI.isInputImageLoaded())
                ).observe(wrapper, { childList: true, subtree: true });
            }
            return WebUI.inputImageLoadedSubject;
        }

        public static getInputImageUrl(): string | null { 
            return WebUI.getInputImage()?.src ?? null;
        }

        private static getInputImage(): HTMLImageElement | null {
            return document.querySelector('#img2img_image img');
        }

        private static getOutputImageSizeFields(img2img: boolean): ImageSizeFields | null {
            let inputs = WebUI.outputImageSizeFields.get(img2img);
            if (!inputs) {
                let prefix = img2img ? 'img2img' : 'txt2img';
                let widthTextbox:  HTMLInputElement | null = document.querySelector(`#${prefix}_width  input[type=number]`);
                let widthSlider:   HTMLInputElement | null = document.querySelector(`#${prefix}_width  input[type=range]`);
                let heightTextbox: HTMLInputElement | null = document.querySelector(`#${prefix}_height input[type=number]`);
                let heightSlider:  HTMLInputElement | null = document.querySelector(`#${prefix}_height input[type=range]`);
                if (!widthTextbox || !widthSlider || !heightTextbox || !heightSlider)
                    return null;

                inputs = { widthTextbox, widthSlider, heightTextbox, heightSlider };
                WebUI.outputImageSizeFields.set(img2img, inputs);
            }
            return inputs;
        }

        private static getResizeByTab(): HTMLDivElement | null {
            return WebUI.resizeByTab ??= document.querySelector('#img2img_tab_resize_by');
        }

        private static getResizeByResolutionPreview(): HTMLSpanElement | null {
            return document.querySelector('#img2img_scale_resolution_preview span[class=resolution]:nth-child(2)');
        }

        public static createWrappedInput(placeholder: string): [HTMLLabelElement, HTMLInputElement] {
            let label = document.createElement('label');
            label.className = `${WebUI.inputClasses} container`;

            let input = document.createElement('input');
            input.className = WebUI.inputClasses;
            input.placeholder = placeholder;

            label.appendChild(input);
            return [label, input];
        }

        public static createButton(text: string): HTMLButtonElement {
            let button = document.createElement('button');
            button.className = WebUI.buttonClasses;
            button.innerText = text;
            button.style.minWidth = 'unset';
            button.style.maxWidth = 'unset';
            return button;
        }

        public static get inputClasses(): string {
            WebUI.svelteInputClass ??= WebUI.getSvelteClassByTagName('textarea');
            return WebUI.svelteInputClass ?? '';
        }

        public static get buttonClasses(): string {
            WebUI.svelteButtonClass ??= WebUI.getSvelteClassByTagName('button');
            return `lg secondary gradio-button tool absolute ${WebUI.svelteButtonClass}`;
        }

        private static getSvelteClassByTagName(tagName: string): string {
            let classNames = document.querySelector(tagName + '[class*="svelte-"]')?.className;
            if (!classNames)
                return '';

            return classNames.split(' ').find(c => c.startsWith('svelte-')) ?? '';
        }
    }
}
