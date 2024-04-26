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

        /** The booleans representing whether each edge is used for resizing */
        this.resize = {};
        /** The margin when the background image is not a square */
        this.padding = {};
        /** The margin to the border of the window */
        this.margin = {};
        /** The step size for moving and resizing */
        this.step = {};

        /** Currently selected row */
        this.cachedRow = null;

        this.registerClick(tab);
        this.registerHover(tab);
        this.registerUp(field, tab);

        image.parentElement.appendChild(this.box);
    }

    get imgBound() {
        return this.img.getBoundingClientRect();
    }

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
            var W = Math.max(mouseX - this.boxBound.left, FC_minimumSize);
            W = Math.min(W, this.imgBound.right - this.padding.left - this.margin.left - this.init.left);

            W = this.step.w * Math.round(W / this.step.w);
            this.box.style.width = `${W}px`;
        } else if (this.resize.L) {
            const rightEdge = style2value(this.box.style.left) + style2value(this.box.style.width);
            var W = Math.max(this.boxBound.right - mouseX, FC_minimumSize)
            W = Math.min(W, rightEdge - this.padding.left);

            W = this.step.w * Math.round(W / this.step.w);
            this.box.style.left = `${rightEdge - W}px`;
            this.box.style.width = `${W}px`;
        }

        if (this.resize.B) {
            var H = Math.max(mouseY - this.boxBound.top, FC_minimumSize);
            H = Math.min(H, this.imgBound.bottom - this.padding.top - this.margin.top - this.init.top);

            H = this.step.h * Math.round(H / this.step.h);
            this.box.style.height = `${H}px`;
        } else if (this.resize.T) {
            const bottomEdge = style2value(this.box.style.top) + style2value(this.box.style.height);
            var H = Math.max(this.boxBound.bottom - mouseY, FC_minimumSize);
            H = Math.min(H, bottomEdge - this.padding.top);

            H = this.step.h * Math.round(H / this.step.h);
            this.box.style.top = `${bottomEdge - H}px`;
            this.box.style.height = `${H}px`;
        }
    }

    /** @param {number} mouseX @param {number} mouseY */
    offsetLogic(mouseX, mouseY) {
        const deltaX = mouseX - this.init.X;
        const deltaY = mouseY - this.init.Y;

        var newLeft = Math.max(this.init.left + deltaX, this.padding.left);
        var newTop = Math.max(this.init.top + deltaY, this.padding.top);

        newLeft = Math.min(newLeft, this.imgBound.width - this.boxBound.width - this.padding.left);
        newTop = Math.min(newTop, this.imgBound.height - this.boxBound.height - this.padding.top);

        newLeft = this.step.w * Math.round(newLeft / this.step.w);
        newTop = this.step.h * Math.round(newTop / this.step.h);

        this.box.style.left = `${newLeft}px`;
        this.box.style.top = `${newTop}px`;
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
        const { naturalWidth, naturalHeight } = this.img;

        var W = 512.0;
        var H = 512.0;

        if (naturalWidth === naturalHeight) {
            this.padding.left = 0.0;
            this.padding.top = 0.0;
        } else if (naturalWidth > naturalHeight) {
            const ratio = naturalHeight / naturalWidth;
            this.padding.left = 0.0;
            this.padding.top = 256.0 * (1.0 - ratio);
            H = 512.0 * ratio;
        } else {
            const ratio = naturalWidth / naturalHeight;
            this.padding.left = 256.0 * (1.0 - ratio);
            this.padding.top = 0.0;
            W = 512.0 * ratio;
        }

        this.step.w = W / 100.0;
        this.step.h = H / 100.0;

        this.img.actualWidth = W;
        this.img.actualHeight = H;

        this.margin.left = this.imgBound.left;
        this.margin.top = this.imgBound.top;

        this.box.style.width = `${W * delta_x}px`;
        this.box.style.height = `${H * delta_y}px`;

        this.box.style.left = `${this.padding.left + W * from_x}px`;
        this.box.style.top = `${this.padding.top + H * from_y}px`;
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
        const { actualWidth, actualHeight } = this.img;
        const { left, right, top, bottom } = this.boxBound;
        const { left: leftPadding, top: topPadding } = this.padding;
        const { left: leftMargin, top: topMargin } = this.margin;

        // console.table({ actualWidth, actualHeight, left, right, top, bottom, leftPadding, topPadding, leftMargin, topMargin });

        const from_x = (left - (leftPadding + leftMargin)) / actualWidth;
        const to_x = (right - (leftPadding + leftMargin)) / actualWidth;
        const from_y = (top - (topPadding + topMargin)) / actualHeight;
        const to_y = (bottom - (topPadding + topMargin)) / actualHeight;

        // console.table({ from_x, to_x, from_y, to_y });

        return `${clamp01(from_x)},${clamp01(to_x)},${clamp01(from_y)},${clamp01(to_y)}`;
    }

}
