class ForgeCoupleBox {

    /** "t2i" | "i2i" */
    #mode = undefined;

    /** The background image */
    #img = undefined;

    /** The bounding of the image */
    get #imgBound() { return this.#img.getBoundingClientRect(); }

    /** The bounding box currently selected */
    #box = undefined;

    /** The bounding of the container */
    get #boxBound() { return this.#box.getBoundingClientRect(); }

    /** Booleans representing whether each edge is used for resizing */
    #resize = {};
    /** Delta between the image and the container, when the image is not a square */
    #padding = {};
    /** The pixel distance to the window edge */
    #margin = {};
    /** The step size (1%) for moving and resizing */
    #step = {};

    /** Currently selected row */
    #cachedRow = null;

    /** @param {Element} image @param {string} mode */
    constructor(image, mode) {
        const box = document.createElement("div");
        box.classList.add(`fc_bbox`);
        box.style.display = "none";

        this.#mode = mode;
        this.#img = image;
        this.#box = box;

        const tab = document.getElementById((mode === "t2i") ? "tab_txt2img" : "tab_img2img");
        this.#registerClick(tab);
        this.#registerHover(tab);
        this.#registerUp(tab);

        image.parentElement.appendChild(box);
    }

    #registerClick(tab) {
        this.#img.addEventListener("mousedown", (e) => {
            if (e.button !== 0)
                return;

            this.isValid = (this.#img.style.cursor != "default");
            this.isResize = (this.#resize.L || this.#resize.R || this.#resize.T || this.#resize.B);

            if (this.isValid) {
                this.#initCoord();

                this.init = {
                    X: e.clientX,
                    Y: e.clientY,
                    left: this.#style2value(this.#box.style.left),
                    top: this.#style2value(this.#box.style.top)
                };

                tab.style.cursor = this.#img.style.cursor;
            }
        });
    }

    #registerHover(tab) {
        tab.addEventListener("mousemove", (e) => {

            if (!this.isValid) {
                this.#checkMouse(e.clientX, e.clientY);
                return;
            }

            if (this.isResize)
                this.#resizeLogic(e.clientX, e.clientY)
            else
                this.#offsetLogic(e.clientX, e.clientY)

        });
    }

    #registerUp(tab) {
        ["mouseup", "mouseleave"].forEach((ev) => {
            tab.addEventListener(ev, (e) => {
                if (!this.isValid || (ev === "mouseup" && e.button !== 0))
                    return;

                const vals = this.#styleToMapping();
                const cells = this.#cachedRow.querySelectorAll("td");

                for (let i = 0; i < vals.length; i++)
                    cells[i].textContent = Number(Math.max(0.0, vals[i])).toFixed(2);

                this.isValid = false;
                tab.style.cursor = "unset";

                ForgeCouple.onEntry(this.#mode);
            });
        });
    }


    /** @param {number} mouseX @param {number} mouseY */
    #resizeLogic(mouseX, mouseY) {
        const FC_minimumSize = 32;

        if (this.#resize.R) {
            const W = this.#clampMinMax(mouseX - this.#boxBound.left, FC_minimumSize,
                this.#imgBound.right + this.#padding.left - this.#margin.left - this.init.left
            );

            this.#box.style.width = `${this.#step.w * Math.round(W / this.#step.w)}px`;
        } else if (this.#resize.L) {
            const rightEdge = this.#style2value(this.#box.style.left) + this.#style2value(this.#box.style.width);
            const W = this.#clampMinMax(this.#boxBound.right - mouseX, FC_minimumSize, rightEdge - this.#padding.left)

            this.#box.style.left = `${rightEdge - this.#step.w * Math.round(W / this.#step.w)}px`;
            this.#box.style.width = `${this.#step.w * Math.round(W / this.#step.w)}px`;
        }

        if (this.#resize.B) {
            const H = this.#clampMinMax(mouseY - this.#boxBound.top, FC_minimumSize,
                this.#imgBound.bottom + this.#padding.top - this.#margin.top - this.init.top
            );

            this.#box.style.height = `${this.#step.h * Math.round(H / this.#step.h)}px`;
        } else if (this.#resize.T) {
            const bottomEdge = this.#style2value(this.#box.style.top) + this.#style2value(this.#box.style.height);
            const H = this.#clampMinMax(this.#boxBound.bottom - mouseY, FC_minimumSize, bottomEdge - this.#padding.top);

            this.#box.style.top = `${bottomEdge - this.#step.h * Math.round(H / this.#step.h)}px`;
            this.#box.style.height = `${this.#step.h * Math.round(H / this.#step.h)}px`;
        }
    }

    /** @param {number} mouseX @param {number} mouseY */
    #offsetLogic(mouseX, mouseY) {
        const deltaX = mouseX - this.init.X;
        const deltaY = mouseY - this.init.Y;

        const newLeft = this.#clampMinMax(this.init.left + deltaX,
            this.#padding.left, this.#imgBound.width - this.#boxBound.width + this.#padding.left);

        const newTop = this.#clampMinMax(this.init.top + deltaY,
            this.#padding.top, this.#imgBound.height - this.#boxBound.height + this.#padding.top);

        this.#box.style.left = `${this.#step.w * Math.round(newLeft / this.#step.w)}px`;
        this.#box.style.top = `${this.#step.h * Math.round(newTop / this.#step.h)}px`;
    }

    /**
     * When a row is selected, display its corresponding bounding box, as well as initialize the coordinates
     * @param {string} color
     * @param {Element} row
     */
    showBox(color, row) {
        this.#cachedRow = row;

        setTimeout(() => {
            this.#initCoord();
            this.#box.style.background = color;
            this.#box.style.display = "block";
        }, 25);
    }

    hideBox() {
        this.#cachedRow = null;
        this.#box.style.display = "none";
    }

    #initCoord() {
        if (this.#cachedRow == null)
            return;

        const [from_x, delta_x, from_y, delta_y] = this.#mappingToStyle(this.#cachedRow);
        const { width, height } = this.#imgBound;

        if (width === height) {
            this.#padding.left = 0.0;
            this.#padding.top = 0.0;
        } else if (width > height) {
            const ratio = height / width;
            this.#padding.left = 0.0;
            this.#padding.top = 256.0 * (1.0 - ratio);
        } else {
            const ratio = width / height;
            this.#padding.left = 256.0 * (1.0 - ratio);
            this.#padding.top = 0.0;
        }

        this.#step.w = width / 100.0;
        this.#step.h = height / 100.0;

        this.#margin.left = this.#imgBound.left;
        this.#margin.top = this.#imgBound.top;

        this.#box.style.width = `${width * delta_x}px`;
        this.#box.style.height = `${height * delta_y}px`;

        this.#box.style.left = `${this.#padding.left + width * from_x}px`;
        this.#box.style.top = `${this.#padding.top + height * from_y}px`;
    }


    /** @param {number} mouseX @param {number} mouseY */
    #checkMouse(mouseX, mouseY) {
        const FC_resizeBorder = 8;

        if (this.#box.style.display == "none") {
            this.#img.style.cursor = "default";
            return;
        }

        const { left, right, top, bottom } = this.#boxBound;

        if (mouseX < left - FC_resizeBorder || mouseX > right + FC_resizeBorder || mouseY < top - FC_resizeBorder || mouseY > bottom + FC_resizeBorder) {
            this.#img.style.cursor = "default";
            return;
        }

        this.#resize.L = mouseX < left + FC_resizeBorder;
        this.#resize.R = mouseX > right - FC_resizeBorder;
        this.#resize.T = mouseY < top + FC_resizeBorder;
        this.#resize.B = mouseY > bottom - FC_resizeBorder;

        if (!(this.#resize.L || this.#resize.T || this.#resize.R || this.#resize.B)) {
            this.#img.style.cursor = "move";
            return;
        }

        if (this.#resize.R && this.#resize.B)
            this.#img.style.cursor = "nwse-resize";
        else if (this.#resize.R && this.#resize.T)
            this.#img.style.cursor = "nesw-resize";
        else if (this.#resize.L && this.#resize.B)
            this.#img.style.cursor = "nesw-resize";
        else if (this.#resize.L && this.#resize.T)
            this.#img.style.cursor = "nwse-resize";
        else if (this.#resize.R || this.#resize.L)
            this.#img.style.cursor = "ew-resize";
        else if (this.#resize.B || this.#resize.T)
            this.#img.style.cursor = "ns-resize";
    }


    /**
     * Convert the table row into coordinate ranges
     * @param {Element} row
     * @returns {number[]}
     */
    #mappingToStyle(row) {
        const cells = row.querySelectorAll("td");

        const from_x = parseFloat(cells[0].textContent);
        const to_x = parseFloat(cells[1].textContent);
        const from_y = parseFloat(cells[2].textContent);
        const to_y = parseFloat(cells[3].textContent);

        return [from_x, to_x - from_x, from_y, to_y - from_y]
    }

    /**
     * Convert the coordinates of bounding box back into string
     * @returns {number[]}
     */
    #styleToMapping() {
        const { width, height } = this.#imgBound;
        const { left, right, top, bottom } = this.#boxBound;
        const { left: leftMargin, top: topMargin } = this.#margin;

        const from_x = (left - leftMargin) / width;
        const to_x = (right - leftMargin) / width;
        const from_y = (top - topMargin) / height;
        const to_y = (bottom - topMargin) / height;

        return [from_x, to_x, from_y, to_y];
    }

    /** @param {number} v @param {number} min @param {number} max @returns {number} */
    #clampMinMax(v, min, max) {
        return Math.min(Math.max(v, min), max);
    }

    /** @param {string} style @returns {number} */
    #style2value(style) {
        try {
            const re = /calc\((-?\d+(?:\.\d+)?)px\)/;
            return parseFloat(style.match(re)[1]);
        } catch {
            return parseFloat(style);
        }
    }
}
