/** Forge Couple Manual Click & Drag */
class FCMCD {
    static x1;
    static y1;
    static x2;
    static y2;

    static COLORS = [
        "hsl(0, 36%, 36%)",
        "hsl(30, 36%, 36%)",
        "hsl(60, 36%, 36%)",
        "hsl(120, 36%, 36%)",
        "hsl(240, 36%, 36%)",
        "hsl(280, 36%, 36%)",
        "hsl(320, 36%, 36%)"
    ];

    static preview(mode) {
        const ex = document.getElementById(`forge_couple_${mode}`);
        const btn = ex.querySelector(".fc_preview");
        btn.click();

        const table = ex.querySelector(".fc_mapping").querySelector("tbody");
        const rows = table.querySelectorAll("tr");

        for (let i = 0; i < rows.length; i++) {
            const bg = getComputedStyle(rows[i]).backgroundColor;
            rows[i].querySelectorAll("td")[2].style.background = `linear-gradient(to right, ${bg} 25%, ${this.COLORS[i % this.COLORS.length]})`;
        }
    }

    static select(mode) {
        const ex = document.getElementById(`forge_couple_${mode}`);
        const table = ex.querySelector(".fc_mapping").querySelector("tbody");
        const rows = table.querySelectorAll("tr");
        const index = ex.querySelector(".fc_index").querySelector("input");

        for (let i = 0; i < rows.length; i++) {
            if (rows[i].querySelector(":focus-within") != null) {
                index.value = i;
                updateInput(index);
                break;
            }
        }
    }
}

onUiLoaded(async () => {
    ["t2i", "i2i"].forEach((mode) => {
        const ex = document.getElementById(`forge_couple_${mode}`);

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
            FCMCD.x1 = (e.clientX - rect.left) / rect.width;
            FCMCD.y1 = (e.clientY - rect.top) / rect.height;
        }

        preview_img.onmouseup = (e) => {
            if (!preview_img.classList.contains("drag"))
                return;
            if (e.button != 0)
                return;

            e.preventDefault();
            const rect = e.target.getBoundingClientRect();
            FCMCD.x2 = (e.clientX - rect.left) / rect.width;
            FCMCD.y2 = (e.clientY - rect.top) / rect.height;

            manual_field.value = `${FCMCD.x1},${FCMCD.x2},${FCMCD.y1},${FCMCD.y2}`;
            updateInput(manual_field);

            preview_img.classList.remove("drag");
        }

        FCMCD.preview(mode);
    });
})
