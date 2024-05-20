class ForgeCoupleImageLoader {

    /** @param {string} filepath @param {method} callback */
    static path2url(filepath, callback) {
        const img = new Image();

        const maxWidth = 1024;
        const maxHeight = 1024;

        img.onload = function () {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');

            var width = img.width;
            var height = img.height;

            while (width > maxWidth || height > maxHeight) {
                width /= 2;
                height /= 2;
            }

            canvas.width = width;
            canvas.height = height;

            ctx.drawImage(img, 0, 0, width, height);
            const resizedDataUrl = canvas.toDataURL('image/jpeg');

            callback(resizedDataUrl);
        };

        img.src = filepath;
    }

    /** @param {Element} image @param {Element[]} btns */
    static setup(image, btns) {

        const [load, load_i2i, clear] = (btns.length === 3) ? btns : [btns[0], null, btns[1]];

        const img_upload = document.createElement("input");
        img_upload.setAttribute("type", "file");
        img_upload.setAttribute("accept", "image/*");

        load.onclick = () => { img_upload.click(); };

        img_upload.onchange = (event) => {
            const file = event.target.files[0];

            if (file != null) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    this.path2url(e.target.result, (new_src) => {
                        image.style.backgroundImage = `url("${new_src}")`
                    });
                };
                reader.readAsDataURL(file);
            }
        };

        if (load_i2i != null) {
            load_i2i.onclick = () => {
                const src = gradioApp().getElementById("img2img_image").querySelector("img")?.src;
                if (src != null) {
                    this.path2url(src, (new_src) => {
                        image.style.backgroundImage = `url("${new_src}")`;
                    });
                }
            };
        }

        clear.onclick = () => { image.style.backgroundImage = "none"; };

        image.parentElement.appendChild(img_upload);
        img_upload.style.display = "none";

    }

}
