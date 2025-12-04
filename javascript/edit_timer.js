class ForgeCoupleObserver {
    static #editTimers = {};

    /**
     * **Reference:** https://github.com/AUTOMATIC1111/stable-diffusion-webui/blob/v1.10.1/javascript/ui.js#L425
     * @param {string} id
     * @param {Element} field
     * @param {Function} callback
     */
    static observe(id, field, callback) {
        const onInput = () => {
            const existingTimer = this.#editTimers[id];
            if (existingTimer) clearTimeout(existingTimer);

            this.#editTimers[id] = setTimeout(callback, 500); // 500 ms
        };

        field.addEventListener("input", onInput);
    }
}
