class ForgeCoupleMaskHandler {

    static #gallery = { "t2i": undefined, "i2i": undefined };

    /** @param {string} mode @param {Element} gallery */
    static setGallery(mode, gallery) { this.#gallery[mode] = gallery; }

    /**
     * After updating the masks, trigger a preview
     * @param {string} mode "t2i" | "i2i"
     */
    static generatePreview(mode) {
        const imgs = this.#gallery[mode].querySelectorAll("img");
        imgs.forEach((img) => { console.log(img); });
    }

}
