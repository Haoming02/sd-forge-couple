onUiLoaded(async () => {
    ["t2i", "i2i"].forEach((mode) => {
        const ex = document.getElementById(`forge_couple_${mode}`);

        const row = ex.querySelector(".controls-wrap");
        const btns = ex.querySelector(".fc_map_btns");

        while (row.firstChild)
            row.firstChild.remove();

        row.appendChild(btns);
    });
})
