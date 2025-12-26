class ForgeCoupleImageLoader {
    /** @param {string} filepath @param {Function} callback */
    static #path2url(filepath, callback) {
        const maxDim = 1024 * 1024;
        const img = new Image();

        img.onload = () => {
            const canvas = document.createElement("canvas");
            const ctx = canvas.getContext("2d");

            let width = img.width;
            let height = img.height;

            while (width * height > maxDim) {
                width = Math.round(width / 2);
                height = Math.round(height / 2);
            }

            canvas.width = width;
            canvas.height = height;

            ctx.drawImage(img, 0, 0, width, height);
            const resizedDataURL = canvas.toDataURL("image/jpeg");

            callback(resizedDataURL);
        };

        img.src = filepath;
    }

    /** @param {HTMLElement} image @param {HTMLButtonElement[]} buttons */
    static setup(image, buttons) {
        const [load, load_i2i, clear] = buttons.length === 3 ? buttons : [buttons[0], null, buttons[1]];

        const imageUpload = document.createElement("input");
        imageUpload.setAttribute("type", "file");
        imageUpload.setAttribute("accept", "image/*");
        imageUpload.style.display = "none";

        imageUpload.onchange = (event) => {
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

        image.parentElement.appendChild(imageUpload);
        load.onclick = () => { imageUpload.click(); };
        clear.onclick = () => { image.style.backgroundImage = "none"; };

        if (load_i2i == null) return;

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
