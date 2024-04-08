/** Forge Couple Manual Click & Drag */
class FCMCD {
    static x1;
    static y1;
    static x2;
    static y2;

    static preview(mode) {
        const ex = document.getElementById(`forge_couple_${mode}`);
        const btn = ex.querySelector(".fc_preview");
        btn.click();
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
    });
})
