const FC_resizeBorder = 8;
const FC_minimumSize = 32;


/** @param {string} style @returns {number} */
function style2value(style) {
    try {
        const re = /calc\((-?\d+(?:\.\d+)?)px\)/;
        return parseFloat(style.match(re)[1]);
    } catch {
        return parseFloat(style);
    }
}

/** @param {number} v @returns {number} */
function clamp01(v) {
    return Math.min(Math.max(v, 0.0), 1.0);
}

/** @param {number} v @param {number} min @param {number} max @returns {number} */
function clampMinMax(v, min, max) {
    return Math.min(Math.max(v, min), max);
}


class ForgeCoupleBox {

    /** @param {Element} image @param {Element} field @param {string} mode */
    constructor(image, field, mode) {
        const tab = gradioApp().getElementById((mode === "t2i") ? "tab_txt2img" : "tab_img2img");

        /** The background image */
        this.img = image;

        /** The bounding box currently selected */
        this.box = document.createElement("div");
        this.box.classList.add(`fc_bbox`);
        this.box.style.display = "none";

        /** Booleans representing whether each edge is used for resizing */
        this.resize = {};
        /** Delta between the image and the container, when the image is not a square */
        this.padding = {};
        /** The pixel distance to the window edge */
        this.margin = {};
        /** The step size (1%) for moving and resizing */
        this.step = {};

        /** Currently selected row */
        this.cachedRow = null;

        this.registerClick(tab);
        this.registerHover(tab);
        this.registerUp(field, tab);

        image.parentElement.appendChild(this.box);
    }

    /** The bounding of the image */
    get imgBound() {
        return this.img.getBoundingClientRect();
    }

    /** The bounding of the container */
    get boxBound() {
        return this.box.getBoundingClientRect();
    }


    registerClick(tab) {
        this.img.addEventListener("mousedown", (e) => {
            if (e.button !== 0)
                return;

            this.isValid = (this.img.style.cursor != "default");
            this.isResize = (this.resize.L || this.resize.R || this.resize.T || this.resize.B);

            if (this.isValid) {
                this.initCoord();

                this.init = {
                    X: e.clientX,
                    Y: e.clientY,
                    left: style2value(this.box.style.left),
                    top: style2value(this.box.style.top)
                };

                tab.style.cursor = this.img.style.cursor;
            }
        });
    }

    registerHover(tab) {
        tab.addEventListener("mousemove", (e) => {

            if (!this.isValid) {
                this.checkMouse(e.clientX, e.clientY);
                return;
            }

            if (this.isResize)
                this.resizeLogic(e.clientX, e.clientY)
            else
                this.offsetLogic(e.clientX, e.clientY)

        });
    }

    registerUp(field, tab) {
        ["mouseup", "mouseleave"].forEach((ev) => {
            tab.addEventListener(ev, (e) => {
                if (!this.isValid || (ev === "mouseup" && e.button !== 0))
                    return;

                field.value = this.styleToMapping();
                updateInput(field);

                this.isValid = false;
                tab.style.cursor = "unset";
            });
        });
    }


    /** @param {number} mouseX @param {number} mouseY */
    resizeLogic(mouseX, mouseY) {
        if (this.resize.R) {
            const W = clampMinMax(mouseX - this.boxBound.left, FC_minimumSize,
                this.imgBound.right + this.padding.left - this.margin.left - this.init.left
            );

            this.box.style.width = `${this.step.w * Math.round(W / this.step.w)}px`;
        } else if (this.resize.L) {
            const rightEdge = style2value(this.box.style.left) + style2value(this.box.style.width);
            const W = clampMinMax(this.boxBound.right - mouseX, FC_minimumSize, rightEdge - this.padding.left)

            this.box.style.left = `${rightEdge - this.step.w * Math.round(W / this.step.w)}px`;
            this.box.style.width = `${this.step.w * Math.round(W / this.step.w)}px`;
        }

        if (this.resize.B) {
            const H = clampMinMax(mouseY - this.boxBound.top, FC_minimumSize,
                this.imgBound.bottom + this.padding.top - this.margin.top - this.init.top
            );

            this.box.style.height = `${this.step.h * Math.round(H / this.step.h)}px`;
        } else if (this.resize.T) {
            const bottomEdge = style2value(this.box.style.top) + style2value(this.box.style.height);
            const H = clampMinMax(this.boxBound.bottom - mouseY, FC_minimumSize, bottomEdge - this.padding.top);

            this.box.style.top = `${bottomEdge - this.step.h * Math.round(H / this.step.h)}px`;
            this.box.style.height = `${this.step.h * Math.round(H / this.step.h)}px`;
        }
    }

    /** @param {number} mouseX @param {number} mouseY */
    offsetLogic(mouseX, mouseY) {
        const deltaX = mouseX - this.init.X;
        const deltaY = mouseY - this.init.Y;

        const newLeft = clampMinMax(this.init.left + deltaX,
            this.padding.left, this.imgBound.width - this.boxBound.width + this.padding.left);

        const newTop = clampMinMax(this.init.top + deltaY,
            this.padding.top, this.imgBound.height - this.boxBound.height + this.padding.top);

        this.box.style.left = `${this.step.w * Math.round(newLeft / this.step.w)}px`;
        this.box.style.top = `${this.step.h * Math.round(newTop / this.step.h)}px`;
    }

    /**
     * When a row is selected, display its corresponding bounding box, as well as initialize the coordinates
     * @param {string} color
     * @param {Element} row
     */
    showBox(color, row) {
        this.cachedRow = row;

        setTimeout(() => {
            this.initCoord();
            this.box.style.background = color;
            this.box.style.display = "block";
        }, 25);
    }

    hideBox() {
        this.cachedRow = null;
        this.box.style.display = "none";
    }

    initCoord() {
        if (this.cachedRow == null)
            return;

        const [from_x, delta_x, from_y, delta_y] = this.mappingToStyle(this.cachedRow);
        const { width, height } = this.imgBound;

        if (width === height) {
            this.padding.left = 0.0;
            this.padding.top = 0.0;
        } else if (width > height) {
            const ratio = height / width;
            this.padding.left = 0.0;
            this.padding.top = 256.0 * (1.0 - ratio);
        } else {
            const ratio = width / height;
            this.padding.left = 256.0 * (1.0 - ratio);
            this.padding.top = 0.0;
        }

        this.step.w = width / 100.0;
        this.step.h = height / 100.0;

        this.margin.left = this.imgBound.left;
        this.margin.top = this.imgBound.top;

        this.box.style.width = `${width * delta_x}px`;
        this.box.style.height = `${height * delta_y}px`;

        this.box.style.left = `${this.padding.left + width * from_x}px`;
        this.box.style.top = `${this.padding.top + height * from_y}px`;
    }


    /** @param {number} mouseX @param {number} mouseY */
    checkMouse(mouseX, mouseY) {
        if (this.box.style.display == "none") {
            this.img.style.cursor = "default";
            return;
        }

        const { left, right, top, bottom } = this.boxBound;

        if (mouseX < left - FC_resizeBorder || mouseX > right + FC_resizeBorder || mouseY < top - FC_resizeBorder || mouseY > bottom + FC_resizeBorder) {
            this.img.style.cursor = "default";
            return;
        }

        this.resize.L = mouseX < left + FC_resizeBorder;
        this.resize.R = mouseX > right - FC_resizeBorder;
        this.resize.T = mouseY < top + FC_resizeBorder;
        this.resize.B = mouseY > bottom - FC_resizeBorder;

        if (!(this.resize.L || this.resize.T || this.resize.R || this.resize.B)) {
            this.img.style.cursor = "move";
            return;
        }

        if (this.resize.R && this.resize.B)
            this.img.style.cursor = "nwse-resize";
        else if (this.resize.R && this.resize.T)
            this.img.style.cursor = "nesw-resize";
        else if (this.resize.L && this.resize.B)
            this.img.style.cursor = "nesw-resize";
        else if (this.resize.L && this.resize.T)
            this.img.style.cursor = "nwse-resize";
        else if (this.resize.R || this.resize.L)
            this.img.style.cursor = "ew-resize";
        else if (this.resize.B || this.resize.T)
            this.img.style.cursor = "ns-resize";
    }


    /**
     * Convert the table row into coordinate ranges
     * @param {Element} row
     * @returns {number[]}
     */
    mappingToStyle(row) {
        const x = row.querySelectorAll("span")[0].textContent;
        const y = row.querySelectorAll("span")[1].textContent;

        const [from_x, to_x] = x.split(":");
        const [from_y, to_y] = y.split(":");

        return [
            parseFloat(from_x),
            parseFloat(to_x - from_x),
            parseFloat(from_y),
            parseFloat(to_y - from_y)
        ]
    }

    /**
     * Convert the coordinates of bounding box back into string
     * @returns {string}
     */
    styleToMapping() {
        const { width, height } = this.imgBound;
        const { left, right, top, bottom } = this.boxBound;
        const { left: leftMargin, top: topMargin } = this.margin;

        const from_x = (left - leftMargin) / width;
        const to_x = (right - leftMargin) / width;
        const from_y = (top - topMargin) / height;
        const to_y = (bottom - topMargin) / height;

        return `${clamp01(from_x)},${clamp01(to_x)},${clamp01(from_y)},${clamp01(to_y)}`;
    }

}
