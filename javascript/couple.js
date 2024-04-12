class ForgeCouple {

    static previewBtn = {};
    static mappingTable = {};
    static manualIndex = {};

    static coords = [[-1, -1], [-1, -1]];

    static COLORS = [
        "hsl(0, 36%, 36%)",
        "hsl(30, 36%, 36%)",
        "hsl(60, 36%, 36%)",
        "hsl(120, 36%, 36%)",
        "hsl(240, 36%, 36%)",
        "hsl(280, 36%, 36%)",
        "hsl(320, 36%, 36%)"
    ];

    static updateColors(mode) {
        const rows = this.mappingTable[mode].querySelectorAll("tr");
        rows.forEach((row, i) => {
            const bg = `var(--table-${(i % 2 == 0) ? "odd" : "even"}-background-fill)`;
            row.style.background = `linear-gradient(to right, ${bg} 80%, ${this.COLORS[i % this.COLORS.length]})`;
        });
    }

    static preview(mode) {
        this.updateColors(mode);
        this.previewBtn[mode].click();
    }

    static onSelect(mode) {
        const rows = Array.from(this.mappingTable[mode].querySelectorAll("tr"));
        rows.forEach((row, i) => {
            if (row.querySelector(":focus-within") != null) {
                this.manualIndex[mode].value = i;
                updateInput(this.manualIndex[mode]);
            }
        });
        this.updateColors(mode);
    }
}

onUiLoaded(async () => {
    ["t2i", "i2i"].forEach((mode) => {
        const ex = document.getElementById(`forge_couple_${mode}`);

        ForgeCouple.previewBtn[mode] = ex.querySelector(".fc_preview");
        ForgeCouple.mappingTable[mode] = ex.querySelector(".fc_mapping").querySelector("tbody");
        ForgeCouple.manualIndex[mode] = ex.querySelector(".fc_index").querySelector("input");

        const row = ex.querySelector(".controls-wrap");
        const btns = ex.querySelector(".fc_map_btns");

        while (row.firstChild)
            row.firstChild.remove();

        row.appendChild(btns);

        const preview_img = ex.querySelector("img");
        preview_img.ondragstart = (e) => { e.preventDefault(); return false; };

        const manual_btn = ex.querySelector(".fc_manual");
        manual_btn.onclick = () => { preview_img.classList.add("drag"); }

        const manual_field = ex.querySelector(".fc_manual_field").querySelector("input");

        preview_img.onmousedown = (e) => {
            if (!preview_img.classList.contains("drag"))
                return;
            if (e.button != 0)
                return;

            e.preventDefault();
            const rect = e.target.getBoundingClientRect();
            ForgeCouple.coords[0][0] = (e.clientX - rect.left) / rect.width;
            ForgeCouple.coords[0][1] = (e.clientY - rect.top) / rect.height;
        }

        preview_img.onmouseup = (e) => {
            if (!preview_img.classList.contains("drag"))
                return;
            if (e.button != 0)
                return;

            e.preventDefault();
            const rect = e.target.getBoundingClientRect();
            ForgeCouple.coords[1][0] = (e.clientX - rect.left) / rect.width;
            ForgeCouple.coords[1][1] = (e.clientY - rect.top) / rect.height;

            manual_field.value = `${ForgeCouple.coords[0][0]},${ForgeCouple.coords[1][0]},${ForgeCouple.coords[0][1]},${ForgeCouple.coords[1][1]}`;
            updateInput(manual_field);

            preview_img.classList.remove("drag");
        }

        setTimeout(() => {
            ForgeCouple.preview(mode);
        }, 100);
    });
})
