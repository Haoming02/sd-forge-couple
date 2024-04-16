class ForgeCoupleBox {

    static resizeBorder = 8;
    static minimumSize = 32;

    /** @param {Element} image @param {Element} field */
    constructor(image, field) {
        this.img = image;
        this.container = image.parentElement;

        this.box = document.createElement("div");
        this.box.classList.add(`fc_bbox`);
        this.box.style.display = "none";

        this.margin = {};
        this.registerClick();
        this.registerHover();
        this.registerUp(field);

        while (this.container.firstElementChild.tagName === "DIV")
            this.container.firstElementChild.remove();

        this.container.appendChild(this.box);
    }

    get imgBound() {
        return this.img.getBoundingClientRect();
    }

    get containerBound() {
        return this.container.getBoundingClientRect();
    }

    get boxBound() {
        return this.box.getBoundingClientRect();
    }


    registerClick() {
        this.img.addEventListener("mousedown", (e) => {
            if (e.button !== 0)
                return;

            this.isValid = (this.img.style.cursor != "default");
            this.isResize = (this.img.style.cursor == "nwse-resize");

            if (this.isValid) {
                this.startX = e.clientX;
                this.startY = e.clientY;
                this.boxX = ForgeCoupleBox.parseStyle(this.box.style.left);
                this.boxY = ForgeCoupleBox.parseStyle(this.box.style.top);
            }
        });
    }

    registerHover() {
        this.img.addEventListener("mousemove", (e) => {
            this.checkMouse(e.clientX, e.clientY);

            if (e.buttons !== 1 || !this.isValid)
                return;

            if (this.isResize) {

                var W = e.clientX - this.boxBound.left;
                var H = e.clientY - this.boxBound.top;

                if (W < ForgeCoupleBox.minimumSize)
                    W = ForgeCoupleBox.minimumSize;
                if (H < ForgeCoupleBox.minimumSize)
                    H = ForgeCoupleBox.minimumSize;

                if (W + this.boxX > this.imgBound.right)
                    W = this.imgBound.right - this.boxX;
                if (H + this.boxY > this.imgBound.bottom)
                    H = this.imgBound.bottom - this.boxY;

                this.box.style.width = `${W}px`;
                this.box.style.height = `${H}px`;

            } else {

                const deltaX = e.clientX - this.startX;
                const deltaY = e.clientY - this.startY;

                var L = this.boxX + deltaX;
                var T = this.boxY + deltaY;

                if (L < this.margin.left)
                    L = this.margin.left;
                if (T < this.margin.top)
                    T = this.margin.top;

                if (L + this.boxBound.width > this.margin.left + this.imgBound.width)
                    L = this.margin.left + this.imgBound.width - this.boxBound.width;
                if (T + this.boxBound.height > this.margin.top + this.imgBound.height)
                    T = this.margin.top + this.imgBound.height - this.boxBound.height;

                this.box.style.left = `${L}px`;
                this.box.style.top = `${T}px`;

            }
        });
    }

    registerUp(field) {
        [this.img, document].forEach((el) => {
            el.addEventListener("mouseup", (e) => {
                if (e.button !== 0 || !this.isValid)
                    return;

                field.value = this.styleToMapping();
                updateInput(field);

                this.isValid = false;
            });
        });
    }


    /** @param {string} color @param {Element} row */
    showBox(color, row) {
        setTimeout(() => {
            const [from_x, to_x, from_y, to_y] = this.mappingToStyle(row);

            this.margin.left = this.imgBound.left - this.containerBound.left;
            this.margin.right = this.containerBound.right - this.imgBound.right;
            this.margin.top = this.imgBound.top - this.containerBound.top;
            this.margin.bottom = this.containerBound.bottom - this.imgBound.bottom;

            this.box.style.width = `${this.imgBound.width * (to_x - from_x)}px`;
            this.box.style.height = `${this.imgBound.height * (to_y - from_y)}px`;

            this.box.style.left = `${this.margin.left + this.imgBound.width * from_x}px`;
            this.box.style.top = `${this.margin.top + this.imgBound.height * from_y}px`;

            this.box.style.display = "block";
            this.box.style.background = color;
        }, 50);
    }

    hideBox() {
        this.box.style.display = "none";
    }


    /** @param {number} mouseX @param {number} mouseY */
    checkMouse(mouseX, mouseY) {
        if (this.box.style.display == "none") {
            this.img.style.cursor = "default";
            return;
        }

        const { left, right, top, bottom } = this.boxBound;
        const { resizeBorder } = ForgeCoupleBox;

        if (mouseX < left || mouseX > right || mouseY < top || mouseY > bottom) {
            this.img.style.cursor = "default";
            return;
        }

        if ((mouseX > right - resizeBorder) && (mouseY > bottom - resizeBorder)) {
            this.img.style.cursor = "nwse-resize";
            return;
        }

        this.img.style.cursor = "move";
    }


    mappingToStyle(row) {
        const x = row.querySelectorAll("span")[0].textContent;
        const y = row.querySelectorAll("span")[1].textContent;

        const [from_x, to_x] = x.split(":");
        const [from_y, to_y] = y.split(":");

        return [parseFloat(from_x), parseFloat(to_x), parseFloat(from_y), parseFloat(to_y)]
    }

    styleToMapping() {
        const from_x = (this.boxBound.left - this.imgBound.left) / this.imgBound.width;
        const to_x = (this.boxBound.right - this.imgBound.left) / this.imgBound.width;
        const from_y = (this.boxBound.top - this.imgBound.top) / this.imgBound.height;
        const to_y = (this.boxBound.bottom - this.imgBound.top) / this.imgBound.height;

        return `${ForgeCoupleBox.clamp(from_x)},${ForgeCoupleBox.clamp(to_x)},${ForgeCoupleBox.clamp(from_y)},${ForgeCoupleBox.clamp(to_y)}`;
    }


    /** @param {string} style @returns {number} */
    static parseStyle(style) {
        try {
            const re = /calc\((-?\d+(?:\.\d+)?)px\)/;
            return parseFloat(style.match(re)[1]);
        } catch {
            return parseFloat(style);
        }
    }

    /** @param {number} v @returns {number} */
    static clamp(v) {
        return Math.min(Math.max(v, 0.0), 1.0);
    }

}
