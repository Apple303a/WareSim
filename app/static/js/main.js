const shipmentForm = document.querySelector("#shipment-form");
const allocationForm = document.querySelector("#allocation-form");
const operationForm = document.querySelector("#operation-form");
const simulationForm = document.querySelector("#simulation-form");
const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (character) => ({
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
})[character]);

if (allocationForm) {
  allocationForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const result = document.querySelector("#allocation-result");
    const submitButton = allocationForm.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    result.className = "mb-4 alert alert-info";
    result.textContent = "Setting warehouse allocation model...";

    try {
      const response = await fetch("/api/storage/allocation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          algorithm: allocationForm.elements.algorithm.value,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Allocation model could not be set.");
      }

      result.className = "mb-4 alert alert-success";
      result.textContent = `Warehouse model set to ${data.allocation_algorithm}.`;
      window.location.reload();
    } catch (error) {
      result.className = "mb-4 alert alert-danger";
      result.textContent = error.message;
      submitButton.disabled = false;
    }
  });
}

if (shipmentForm) {
  shipmentForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const result = document.querySelector("#shipment-result");
    const submitButton = shipmentForm.querySelector('button[type="submit"]');
    const formData = new FormData(shipmentForm);
    const payload = Object.fromEntries(formData.entries());
    payload.size = Number(payload.size);
    submitButton.disabled = true;
    result.className = "mt-4 alert alert-info";
    result.textContent = "Creating shipment...";

    try {
      const response = await fetch("/api/shipments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Shipment could not be created.");
      }

      const blocks = data.allocation_metadata.allocated_blocks;
      result.className = "mt-4 alert alert-success";
      result.replaceChildren();
      const message = document.createElement("p");
      message.textContent =
        `Created ${data.shipment.shipment_id}: ${blocks.length} block(s) ` +
        `allocated at positions ${blocks.map((block) => block.position).join(", ")}.`;
      result.append(message);
      const link = document.createElement("a");
      link.href = "/";
      link.textContent = "View updated dashboard";
      result.append(link);
      shipmentForm.reset();
    } catch (error) {
      result.className = "mt-4 alert alert-danger";
      result.textContent = error.message;
    } finally {
      submitButton.disabled = false;
    }
  });
}

if (operationForm) {
  operationForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const result = document.querySelector("#operation-result");
    const button = operationForm.querySelector('button[type="submit"]');
    const formData = new FormData(operationForm);
    const payload = Object.fromEntries(formData.entries());
    for (const key of [
      "worker_position",
      "arrival_time",
      "seek_time_per_position",
      "fixed_io_latency",
      "read_transfer_rate",
      "write_transfer_rate",
    ]) {
      payload[key] = Number(payload[key]);
    }
    payload.timing = {
      seek_time_per_position: payload.seek_time_per_position,
      fixed_io_latency: payload.fixed_io_latency,
      read_transfer_rate: payload.read_transfer_rate,
      write_transfer_rate: payload.write_transfer_rate,
    };
    button.disabled = true;
    result.className = "mt-4 alert alert-info";
    result.textContent = "Scheduling block requests...";

    try {
      const response = await fetch("/api/operations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Operation could not be scheduled.");
      }

      result.className = "mt-4";
      result.replaceChildren();
      const title = document.createElement("h2");
      title.className = "h4";
      title.textContent = `${data.operation} — ${data.shipment_id}`;
      result.append(title);
      const table = document.createElement("div");
      table.className = "table-responsive";
      const rows = Object.entries(data.results).map(([name, item]) => {
        const metrics = item.metrics;
        return `<tr><th>${escapeHtml(name.toUpperCase())}</th><td>${item.execution_order.map(escapeHtml).join(", ")}</td><td>${item.movement_path.map(escapeHtml).join(" → ")}</td><td>${item.total_movement}</td><td>${metrics.average_waiting_time}</td><td>${metrics.average_turnaround_time}</td><td>${metrics.throughput}</td><td>${metrics.average_read_latency}</td><td>${metrics.average_write_latency}</td></tr>`;
      }).join("");
      table.innerHTML = `<table class="table table-sm table-striped"><thead><tr><th>Algorithm</th><th>Execution order</th><th>Movement path</th><th>Movement</th><th>Avg wait</th><th>Avg turnaround</th><th>Requests / time</th><th>Read latency</th><th>Write latency</th></tr></thead><tbody>${rows}</tbody></table>`;
      result.append(table);
    } catch (error) {
      result.className = "mt-4 alert alert-danger";
      result.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });
}

document.querySelectorAll(".delete-shipment").forEach((button) => {
  button.addEventListener("click", async () => {
    const shipmentId = button.dataset.shipmentId;
    if (!window.confirm(`Delete shipment ${shipmentId} and free its boxes?`)) {
      return;
    }

    const message = document.querySelector("#dashboard-message");
    button.disabled = true;
    message.className = "alert alert-info";
    message.textContent = `Deleting shipment ${shipmentId}...`;

    try {
      const response = await fetch(
        `/api/shipments/${encodeURIComponent(shipmentId)}`,
        { method: "DELETE" },
      );
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Shipment could not be deleted.");
      }

      window.location.reload();
    } catch (error) {
      message.className = "alert alert-danger";
      message.textContent = error.message;
      button.disabled = false;
    }
  });
});

if (simulationForm) {
  const matrixButtons = Array.from(
    document.querySelectorAll(".run-simulation-cell"),
  );
  const runAllButton = document.querySelector("#run-all-simulations");
  const message = document.querySelector("#simulation-message");
  const summary = document.querySelector("#workload-summary");
  const resultPanel = document.querySelector("#simulation-result");
  const generateButton = simulationForm.querySelector('button[type="submit"]');
  const workloadDetails = document.querySelector("#workload-details");
  const comparisonMetric = document.querySelector("#comparison-metric");
  const comparisonStatus = document.querySelector("#comparison-status");
  const winnerSummary = document.querySelector("#winner-summary");
  const comparisonChart = document.querySelector("#comparison-chart");
  let currentWorkload = JSON.parse(
    document.querySelector("#initial-workload").textContent,
  );
  let currentResults = JSON.parse(
    document.querySelector("#initial-simulation-results").textContent,
  );
  let runningCellCount = 0;
  let runningAll = false;

  const renderWorkload = (workload) => {
    if (!workload) {
      return;
    }
    workloadDetails.hidden = false;
    const lifecycle = document.createElement("div");
    lifecycle.className = "table-responsive";
    const events = workload.lifecycle_events.map((event) =>
      `<tr><td>${event.sequence}</td><td><span class="badge text-bg-${event.action === "DELETE" ? "danger" : event.action === "RETAIN" ? "secondary" : "success"}">${escapeHtml(event.action)}</span></td><td>${escapeHtml(event.phase)}</td><td>${escapeHtml(event.shipment_id)}</td><td>${event.size}</td><td>${escapeHtml(event.detail)}</td></tr>`,
    ).join("");
    lifecycle.innerHTML = `<table class="table table-sm table-striped align-middle"><thead><tr><th>#</th><th>Action</th><th>Phase</th><th>Shipment</th><th>Size</th><th>What happened</th></tr></thead><tbody>${events}</tbody></table>`;
    document.querySelector("#lifecycle-log").replaceChildren(lifecycle);

    const operations = document.createElement("div");
    const rows = workload.operations.map((operation) =>
      `<tr><td>${escapeHtml(operation.operation_id)}</td><td>${escapeHtml(operation.operation)}</td><td>${escapeHtml(operation.shipment_id)}</td><td>${operation.arrival_time}</td><td>${operation.block_count}</td></tr>`,
    ).join("");
    operations.innerHTML = `<table class="table table-sm table-striped"><thead><tr><th>Operation</th><th>Type</th><th>Shipment</th><th>Arrival (sim units)</th><th>Block requests</th></tr></thead><tbody>${rows}</tbody></table>`;
    document.querySelector("#operation-log").replaceChildren(operations);
    document.querySelector("#operation-count-label").textContent =
      workload.operations.length;
  };

  const metricsForComparison = {
    turnaround: {
      label: "Average turnaround (time units)",
      lowerIsBetter: true,
      getValue: (result) => result.schedule.metrics.average_turnaround_time,
    },
    movement: {
      label: "Total head movement (positions)",
      lowerIsBetter: true,
      getValue: (result) => result.schedule.total_movement,
    },
    throughput: {
      label: "Request throughput (requests / time unit)",
      lowerIsBetter: false,
      getValue: (result) => result.schedule.metrics.throughput,
    },
    external: {
      label: "External fragmentation (free boxes)",
      lowerIsBetter: true,
      getValue: (result) => result.storage_metrics.external_fragmentation_units,
    },
  };
  const allocationColors = {
    contiguous: "#0d6efd",
    linked: "#198754",
    indexed: "#6f42c1",
  };

  const renderComparison = () => {
    const definition = metricsForComparison[comparisonMetric.value];
    const completed = Object.entries(currentResults)
      .filter(([, result]) => result.allocation_success)
      .map(([key, result]) => ({ key, result, value: definition.getValue(result) }));
    const failures = Object.values(currentResults)
      .filter((result) => !result.allocation_success).length;
    comparisonStatus.textContent =
      `${completed.length} successful and ${failures} failed of 18 combinations.`;
    const rank = (left, right) => definition.lowerIsBetter
      ? left.value - right.value
      : right.value - left.value;
    completed.sort((left, right) => rank(left, right) || left.key.localeCompare(right.key));
    winnerSummary.replaceChildren();
    comparisonChart.replaceChildren();

    if (!completed.length) {
      winnerSummary.innerHTML = `<div class="col-12"><div class="alert alert-secondary mb-0">Run one cell or all 18 combinations to see a winner and loser.</div></div>`;
      return;
    }

    const createRankCard = (title, item, style) => {
      const card = document.createElement("div");
      card.className = "col-md-6";
      const body = document.createElement("div");
      body.className = `card h-100 ${style}`;
      const content = document.createElement("div");
      content.className = "card-body";
      const heading = document.createElement("h3");
      heading.className = "h6 card-title";
      heading.textContent = title;
      const value = document.createElement("p");
      value.className = "h5 mb-1";
      value.textContent = item.key.replace(":", " + ").toUpperCase();
      const detail = document.createElement("p");
      detail.className = "mb-0 small";
      detail.textContent = `${definition.label}: ${item.value}`;
      content.append(heading, value, detail);
      body.append(content);
      card.append(body);
      return card;
    };
    winnerSummary.append(
      createRankCard("Winner for this metric", completed[0], "border-success"),
      createRankCard("Lowest-ranked for this metric", completed[completed.length - 1], "border-danger"),
    );
    if (failures) {
      const note = document.createElement("div");
      note.className = "col-12";
      note.innerHTML = `<div class="alert alert-warning mb-0">${failures} combination(s) could not allocate the workload. Failed allocations are excluded from this metric ranking.</div>`;
      winnerSummary.append(note);
    }

    const maximum = Math.max(...completed.map((item) => item.value), 0);
    const chartRows = document.createElement("div");
    chartRows.className = "comparison-bars";
    completed.forEach((item) => {
      const [allocation, scheduler] = item.key.split(":");
      const row = document.createElement("div");
      row.className = "comparison-bar-row";
      const label = document.createElement("span");
      label.className = "comparison-bar-label";
      label.textContent = `${allocation} · ${scheduler.toUpperCase()}`;
      const track = document.createElement("span");
      track.className = "comparison-bar-track";
      const fill = document.createElement("span");
      fill.className = "comparison-bar-fill";
      fill.style.backgroundColor = allocationColors[allocation];
      fill.style.width = `${maximum > 0 ? item.value / maximum * 100 : 0}%`;
      track.append(fill);
      const value = document.createElement("span");
      value.className = "comparison-bar-value";
      value.textContent = String(item.value);
      row.setAttribute("aria-label", `${label.textContent}: ${item.value} ${definition.label}`);
      row.append(label, track, value);
      chartRows.append(row);
    });
    const note = document.createElement("p");
    note.className = "small text-muted mt-2 mb-0";
    note.textContent = `${definition.label}. Bars are ranked best to worst; colors identify allocation methods.`;
    comparisonChart.append(chartRows, note);
  };

  renderWorkload(currentWorkload);
  renderComparison();
  comparisonMetric.addEventListener("change", renderComparison);

  const renderResult = (key, result) => {
    const storage = result.storage_metrics;
    const cells = result.warehouse_map.map((box) =>
      `<div class="warehouse-box ${box.occupied ? "occupied" : "free"}" title="Position ${box.position}${box.occupied ? `: ${escapeHtml(box.block_id)}` : ""}"><span>${box.position}</span>${box.occupied ? `<strong>${escapeHtml(box.shipment_id)}</strong>` : ""}</div>`,
    ).join("");
    if (!result.allocation_success) {
      resultPanel.innerHTML = `
        <h2 class="h4">Results: ${escapeHtml(key)}</h2>
        <div class="alert alert-warning">Allocation failed: ${escapeHtml(result.allocation_error)}</div>
        <p>Storage state when allocation stopped: ${storage.occupied_boxes}/${storage.total_boxes} boxes occupied;
          ${storage.internal_fragmentation_units} internal-fragmentation units;
          ${storage.external_fragmentation_units} free boxes outside the largest extent
          (${storage.external_fragmentation_pct}%). Largest free extent: ${storage.largest_free_extent} boxes.</p>
        <h3 class="h6">Warehouse layout</h3><div class="warehouse-map">${cells}</div>`;
      return;
    }
    const metrics = result.schedule.metrics;
    const timeline = result.schedule.execution_timeline.map((item) =>
      `<tr><td>${escapeHtml(item.request_id)}</td><td>${escapeHtml(item.operation)}</td><td>${item.position}</td><td>${item.start_time}</td><td>${item.completion_time}</td><td>${item.waiting_time}</td><td>${item.turnaround_time}</td></tr>`,
    ).join("");
    resultPanel.innerHTML = `
      <h2 class="h4">Results: ${escapeHtml(key)}</h2>
      <div class="row g-3">
        <div class="col-lg-6"><h3 class="h6">Storage / fragmentation</h3>
          <div class="table-responsive"><table class="table table-sm"><tbody>
            <tr><th>Utilization</th><td>${storage.storage_utilization_pct}% (${storage.occupied_boxes}/${storage.total_boxes} boxes)</td></tr>
            <tr><th>Internal fragmentation</th><td>${storage.internal_fragmentation_units} units</td></tr>
            <tr><th>External fragmentation</th><td>${storage.external_fragmentation_units} free boxes outside the largest extent (${storage.external_fragmentation_pct}%)</td></tr>
            <tr><th>Largest free extent</th><td>${storage.largest_free_extent} boxes</td></tr>
          </tbody></table></div>
        </div>
        <div class="col-lg-6"><h3 class="h6">I/O performance</h3>
          <div class="table-responsive"><table class="table table-sm"><tbody>
            <tr><th>Total movement</th><td>${result.schedule.total_movement} positions</td></tr>
            <tr><th>Average wait / response</th><td>${metrics.average_waiting_time} / ${metrics.average_response_time} time units</td></tr>
            <tr><th>Average turnaround</th><td>${metrics.average_turnaround_time} time units</td></tr>
            <tr><th>Average READ / WRITE latency</th><td>${metrics.average_read_latency} / ${metrics.average_write_latency} time units</td></tr>
            <tr><th>Average seek time</th><td>${metrics.average_seek_time} time units per request</td></tr>
            <tr><th>READ / WRITE throughput</th><td>${metrics.read_throughput_units_per_time} / ${metrics.write_throughput_units_per_time} units per time</td></tr>
            <tr><th>Request throughput</th><td>${metrics.throughput} requests per time</td></tr>
          </tbody></table></div>
        </div>
      </div>
      <h3 class="h6 mt-3">Warehouse layout</h3><div class="warehouse-map">${cells}</div>
      <p class="mt-2"><strong>Worker movement path:</strong> ${result.schedule.movement_path.map(escapeHtml).join(" → ")}</p>
      <h3 class="h6 mt-3">Request timeline</h3>
      <div class="table-responsive"><table class="table table-sm table-striped">
        <thead><tr><th>Request</th><th>Type</th><th>Position</th><th>Start</th><th>Complete</th><th>Wait</th><th>Turnaround</th></tr></thead>
        <tbody>${timeline}</tbody>
      </table></div>`;
  };

  const runCell = async (button) => {
    const allocation = button.dataset.allocation;
    const scheduler = button.dataset.scheduler;
    const key = `${allocation}:${scheduler}`;
    runningCellCount += 1;
    generateButton.disabled = true;
    button.disabled = true;
    button.textContent = "Running...";
    message.className = "mt-3 alert alert-info";
    message.textContent = `Simulating ${key}...`;
    try {
      const response = await fetch("/api/simulations/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          allocation_algorithm: allocation,
          scheduling_algorithm: scheduler,
          workload_id: button.dataset.workloadId,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Simulation failed.");
      }
      const result = data.result;
      const allocationFailed = !result.allocation_success;
      currentResults[data.key] = result;
      renderComparison();
      button.textContent = allocationFailed
        ? "Allocation failed"
        : `Run again | move ${result.schedule.total_movement}`;
      const cellSummary = button.nextElementSibling;
      if (allocationFailed) {
        cellSummary.textContent =
          `Allocation failed; external frag ${result.storage_metrics.external_fragmentation_units} ` +
          `(${result.storage_metrics.external_fragmentation_pct}%).`;
      } else {
        cellSummary.textContent =
          `Turnaround ${result.schedule.metrics.average_turnaround_time}; ` +
          `movement ${result.schedule.total_movement}; ` +
          `external frag ${result.storage_metrics.external_fragmentation_units}.`;
      }
      renderResult(data.key, result);
      message.className = "mt-3 alert alert-success";
      message.textContent = allocationFailed
        ? `${key} completed with an allocation failure.`
        : `Completed ${key}.`;
      return true;
    } catch (error) {
      button.textContent = "Retry";
      message.className = "mt-3 alert alert-danger";
      message.textContent = `${key}: ${error.message}`;
      return false;
    } finally {
      runningCellCount -= 1;
      button.disabled = runningAll;
      if (runningCellCount === 0 && !runningAll) {
        generateButton.disabled = false;
      }
    }
  };

  if (simulationForm) {
    simulationForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const seedInput = document.querySelector("#demo-seed");
      const seed = Number(seedInput.value);
      generateButton.disabled = true;
      message.className = "mt-3 alert alert-info";
      message.textContent = `Building the demo workload for seed ${seed}...`;
      try {
        const response = await fetch("/api/simulations/workload", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            shipment_count: 12,
            replacement_count: 4,
            minimum_size: 50,
            maximum_size: 300,
            operation_count: 40,
            read_percent: 50,
            delete_percent: 25,
            seed,
            arrival_span: 100,
          }),
        });
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.error || "Workload could not be generated.");
        }
        currentWorkload = data;
        currentResults = {};
        renderWorkload(data);
        renderComparison();
        matrixButtons.forEach((cell) => {
          cell.disabled = true;
          cell.textContent = "Simulate";
          cell.dataset.workloadId = data.workload_id;
          cell.nextElementSibling.textContent = "";
        });
        resultPanel.replaceChildren();
        summary.className = "alert alert-success";
        summary.textContent =
          `Seed ${data.config.seed}: ${data.shipment_count} initial shipments, ` +
          `${data.deleted_shipment_count} deleted, ` +
          `${data.shipment_count - data.deleted_shipment_count} retained, ` +
          `${data.replacement_count} replacements; ${data.operation_count} shipment I/O ` +
          `operations expand to ${data.block_request_count} block requests.`;
        seedInput.value = String((seed + 1) % (2 ** 31));
        generateButton.textContent = `Run new demo (seed ${seedInput.value})`;
        await runAllCells();
      } catch (error) {
        message.className = "mt-3 alert alert-danger";
        message.textContent = error.message;
      } finally {
        generateButton.disabled = false;
      }
    });
  }

  matrixButtons.forEach((button) => {
    button.addEventListener("click", () => runCell(button));
  });

  const runAllCells = async () => {
    if (!currentWorkload) {
      return;
    }
    runningAll = true;
    runAllButton.disabled = true;
    matrixButtons.forEach((button) => {
      button.disabled = true;
    });
    for (const button of matrixButtons) {
      if (!await runCell(button)) {
        break;
      }
    }
    runningAll = false;
    matrixButtons.forEach((button) => {
      button.disabled = false;
    });
    runAllButton.disabled = false;
    generateButton.disabled = false;
  };

  if (runAllButton) {
    runAllButton.addEventListener("click", runAllCells);
  }
}
