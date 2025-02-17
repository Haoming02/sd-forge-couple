class ForgeCoupleImageLoader {
    static #maxDim = 1024 * 1024;

    /** @param {string} filepath @param {Function} callback */
    static #path2url(filepath, callback) {
        const img = new Image();

        img.onload = () => {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');

            let width = img.width;
            let height = img.height;

            while (width * height > this.#maxDim) {
                width = Math.round(width / 2);
                height = Math.round(height / 2);
            }

            canvas.width = width;
            canvas.height = height;

            ctx.drawImage(img, 0, 0, width, height);
            const resizedDataURL = canvas.toDataURL('image/jpeg');

            callback(resizedDataURL);
        };

        img.src = filepath;
    }

    /** @param {Element} image @param {Element[]} btns */
    static setup(image, btns) {
        const [load, load_i2i, clear] = (btns.length === 3) ? btns : [btns[0], null, btns[1]];

        const img_upload = document.createElement("input");
        img_upload.setAttribute("type", "file");
        img_upload.setAttribute("accept", "image/*");
        img_upload.style.display = "none";

        img_upload.onchange = (event) => {
            const file = event.target.files[0];

            if (file != null) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    this.#path2url(e.target.result, (new_src) => {
                        image.style.backgroundImage = `url("${new_src}")`;
                    });
                };
                reader.readAsDataURL(file);
            }
        };

        image.parentElement.appendChild(img_upload);
        load.onclick = () => { img_upload.click(); };
        clear.onclick = () => { image.style.backgroundImage = "none"; };

        if (load_i2i == null)
            return;

        load_i2i.onclick = () => {
            const src = document.getElementById("img2img_image").querySelector("img")?.src;
            if (src != null) {
                this.#path2url(src, (new_src) => {
                    image.style.backgroundImage = `url("${new_src}")`;
                });
            }
        };
    }
}
