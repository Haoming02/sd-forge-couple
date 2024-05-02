class ForgeCoupleImageLoader {

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
                    image.style.backgroundImage = `url("${e.target.result}")`
                };
                reader.readAsDataURL(file);
            }
        };

        if (load_i2i != null) {
            load_i2i.onclick = () => {
                const src = gradioApp().getElementById("img2img_image").querySelector("img")?.src;
                if (src != null)
                    image.style.backgroundImage = `url("${src}")`;
            };
        }

        clear.onclick = () => { image.style.backgroundImage = "none"; };

        image.parentElement.appendChild(img_upload);
        img_upload.style.display = "none";

    }

}
