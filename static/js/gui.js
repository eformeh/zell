document.addEventListener("DOMContentLoaded", () => {
    const fileInput = document.querySelector("#source_file");
    if (fileInput) {
        fileInput.addEventListener("change", () => {
            const label = document.querySelector("#file-name");
            label.textContent = fileInput.files.length ? fileInput.files[0].name : "No file selected";
        });
    }

    document.querySelectorAll("[data-repeat-section]").forEach((section) => {
        section.querySelector("[data-add-row]")?.addEventListener("click", () => {
            const template = section.querySelector("template");
            section.querySelector("[data-rows]").appendChild(template.content.cloneNode(true));
        });
        section.addEventListener("click", (event) => {
            if (event.target.matches("[data-remove-row]")) {
                event.target.closest(".repeat-row")?.remove();
            }
        });
    });

    const search = document.querySelector("[data-table-search]");
    const filterGroup = document.querySelector("[data-table-filter]");
    if (search && filterGroup) {
        const table = document.querySelector(`#${search.dataset.tableSearch}`);
        let activeFilter = "all";
        const refresh = () => {
            const query = search.value.trim().toLowerCase();
            table.querySelectorAll("tbody tr").forEach((row) => {
                const matchesText = !query || row.textContent.toLowerCase().includes(query);
                const matchesStatus = activeFilter === "all" || row.dataset.status === activeFilter;
                row.hidden = !(matchesText && matchesStatus);
            });
        };
        search.addEventListener("input", refresh);
        filterGroup.addEventListener("click", (event) => {
            const button = event.target.closest("button[data-filter]");
            if (!button) return;
            filterGroup.querySelectorAll("button").forEach((item) => item.classList.remove("active"));
            button.classList.add("active");
            activeFilter = button.dataset.filter;
            refresh();
        });
    }

    if (window.CAC_JOB_ID) {
        pollJob(window.CAC_JOB_ID);
    }
});

async function pollJob(jobId) {
    const fill = document.querySelector("#progress-fill");
    const stage = document.querySelector("#job-stage");
    const count = document.querySelector("#job-count");
    const title = document.querySelector("#job-title");
    const result = document.querySelector("#job-result");
    try {
        const response = await fetch(`/api/jobs/${jobId}`, { cache: "no-store" });
        const job = await response.json();
        const percent = job.total ? Math.round((job.completed / job.total) * 100) : 0;
        fill.style.width = `${percent}%`;
        stage.textContent = job.stage === "pdf" ? "Generating PDF reports" : job.stage === "html" ? "Rendering HTML reports" : "Preparing";
        count.textContent = `${job.completed || 0} / ${job.total || 0}`;
        if (job.status === "completed") {
            fill.style.width = "100%";
            title.textContent = "Run complete";
            stage.textContent = `${job.summary.pdf_generated} PDFs · ${job.summary.failures.length} failures`;
            result.innerHTML = `<a class="button button-primary" href="/runs/${encodeURIComponent(job.run)}">Open completed run</a>`;
            return;
        }
        if (job.status === "failed") {
            title.textContent = "Generation failed";
            stage.textContent = job.error || "Unknown error";
            result.innerHTML = `<a class="button" href="/">Start a new run</a>`;
            return;
        }
        window.setTimeout(() => pollJob(jobId), 700);
    } catch (error) {
        title.textContent = "Connection interrupted";
        stage.textContent = "Retrying status check";
        window.setTimeout(() => pollJob(jobId), 1600);
    }
}
