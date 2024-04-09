namespace ForgeCouple {
    export class CustomRegionControl {
        private static readonly colors = ['red', 'orange', 'yellow', 'green', 'blue', 'violet', 'purple', 'white'];
        private static readonly instances = new Map<boolean, CustomRegionControl>();

        public static refreshTxt2img(): void {
            CustomRegionControl.refresh(false);
        }

        public static refreshImg2img(): void {
            CustomRegionControl.refresh(true);
        }

        public static refresh(forImg2img: boolean): void {
            let instance = this.instances.get(forImg2img);
            if (!instance) {
                let suffix = forImg2img ? 'img2img' : 'txt2img';
                let groupElem = document.querySelector(`#forge-couple--adv-group-${suffix}`) as HTMLDivElement | null;
                let regionsInputElem = document.querySelector(`#forge-couple--adv-regions-${suffix} textarea`) as HTMLTextAreaElement | null;
                if (!groupElem || !regionsInputElem)
                    return;
                
                instance = new CustomRegionControl(groupElem, regionsInputElem, forImg2img);
                this.instances.set(forImg2img, instance);
            }
            instance.onImageSizeChanged();
            instance.refreshRegions();
        }

        private regions: Region[] = [];
        private promptPresenter: PromptListControl;
        private boxPresenter: BoxCanvasControl;
        private sendingToGradio: boolean = false;

        constructor(
            containerElem: HTMLElement,
            private regionsInputElem: HTMLTextAreaElement,
            private forImg2img: boolean
        ) {
            this.promptPresenter = new PromptListControl(containerElem, CustomRegionControl.colors.length);
            this.boxPresenter = new BoxCanvasControl(containerElem, forImg2img);

            WebUI.getOutputImageSizeSubject(forImg2img)?.subscribe(_ => this.onImageSizeChanged());

            this.promptPresenter.addRequested.subscribe(() => this.addRegion());
            this.promptPresenter.regionSelected.subscribe(index => this.boxPresenter.selectRegion(index));
            this.promptPresenter.regionChanged.subscribe(index => this.onPromptChanged(index));
            this.promptPresenter.removeRequested.subscribe(index => this.removeRegion(index));

            this.boxPresenter.regionSelected.subscribe(index => this.promptPresenter.selectRegion(index));
            this.boxPresenter.regionChanged.subscribe(_ => this.sendRegionsToGradio());

            this.addRegion();
        }

        public refreshRegions(): void {
            if (this.sendingToGradio) {
                this.sendingToGradio = false;
                return;
            }

            let regions = this.regionsInputElem.value.split('\n').filter(l => l.trim().length > 0).map(Region.deserialize);
            
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

        private onImageSizeChanged(): void {
            let size = WebUI.getOutputImageSize(this.forImg2img) ?? { width: 512, height: 512 };
            
            let aspect = size.height > 0 ? size.width / size.height : 1;
            this.boxPresenter.setAspectRatio(aspect);
        }

        private addRegion(): void {
            if (this.regions.length >= CustomRegionControl.colors.length)
                return;

            let region = new Region();
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

        private onPromptChanged(index: number): void {
            this.boxPresenter.updateRegion(index);
            this.sendRegionsToGradio();
        }

        private removeRegion(index: number): void {
            this.regions.splice(index, 1);
            this.promptPresenter.removeRegion(index);
            this.boxPresenter.removeRegion(index);
            this.sendRegionsToGradio();
        }

        private sendRegionsToGradio(): void {
            let serializedRegions = this.regions.map(r => r.serialize()).join('\n');
            if (serializedRegions === this.regionsInputElem.value)
                return;

            this.sendingToGradio = true;
            this.regionsInputElem.value = serializedRegions;
            this.regionsInputElem.dispatchEvent(new Event('input'));
        }
    }
}
