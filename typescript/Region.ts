namespace ForgeCouple {
    export class Region {
        public enabled: boolean = true;
        public color: string = '';
        public x = 0.4;
        public y = 0.4;
        public width = 0.2;
        public height = 0.2;
        public prompt = '';
        public weight = 1;

        public getClientRect(containerRect: DOMRect): DOMRect {
            return new DOMRect(
                containerRect.left + this.x * containerRect.width,
                containerRect.top  + this.y * containerRect.height,
                this.width  * containerRect.width,
                this.height * containerRect.height
            );
        }

        public setClientRect(containerRect: DOMRect, regionRect: DOMRect): void {
            this.x = (regionRect.left - containerRect.left) / containerRect.width;
            this.y = (regionRect.top - containerRect.top) / containerRect.height;
            this.width = regionRect.width / containerRect.width;
            this.height = regionRect.height / containerRect.height;
        }

        public serialize(): string {
            const prec = 5;
            return `${this.enabled ? 1 : 0},${this.x.toFixed(prec)},${this.y.toFixed(prec)},${this.width.toFixed(prec)},${this.height.toFixed(prec)},${this.weight},${this.prompt}`;
        }

        static deserialize(data: string): Region {
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
}
