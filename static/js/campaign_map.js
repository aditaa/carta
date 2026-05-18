(function () {
  const shell = document.querySelector(".map-shell");
  const canvas = document.getElementById("map-canvas");
  if (!shell || !canvas || !shell.dataset.mapImage) {
    return;
  }

  const ctx = canvas.getContext("2d");
  const readouts = {
    hex: shell.querySelector('[data-map-readout="hex"]'),
    zoom: shell.querySelector('[data-map-readout="zoom"]'),
  };
  const mapImage = new Image();
  const mapWidth = Number(shell.dataset.mapWidth || 5234);
  const mapHeight = Number(shell.dataset.mapHeight || 3072);
  const playableWidth = Number(shell.dataset.playableWidth || mapWidth);
  const hexSize = Number(shell.dataset.hexSize || 22);
  const hexOrigin = {
    x: Number(shell.dataset.hexOriginX || 7),
    y: Number(shell.dataset.hexOriginY || 12),
  };
  const view = {
    scale: 1,
    offsetX: 0,
    offsetY: 0,
  };
  const drag = {
    active: false,
    x: 0,
    y: 0,
  };

  function resizeCanvas() {
    const rect = canvas.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.max(Math.floor(rect.width * ratio), 1);
    canvas.height = Math.max(Math.floor(rect.height * ratio), 1);
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    draw();
  }

  function hexToPixel(q, r) {
    return {
      x: hexOrigin.x + hexSize * Math.sqrt(3) * (q + r / 2),
      y: hexOrigin.y + hexSize * 1.5 * r,
    };
  }

  function pixelToHex(x, y) {
    const localX = x - hexOrigin.x;
    const localY = y - hexOrigin.y;
    const q = (Math.sqrt(3) / 3 * localX - 1 / 3 * localY) / hexSize;
    const r = (2 / 3 * localY) / hexSize;
    return roundHex(q, -q - r, r);
  }

  function roundHex(q, s, r) {
    let roundedQ = Math.round(q);
    let roundedS = Math.round(s);
    let roundedR = Math.round(r);
    const qDiff = Math.abs(roundedQ - q);
    const sDiff = Math.abs(roundedS - s);
    const rDiff = Math.abs(roundedR - r);

    if (qDiff > sDiff && qDiff > rDiff) {
      roundedQ = -roundedS - roundedR;
    } else if (sDiff > rDiff) {
      roundedS = -roundedQ - roundedR;
    } else {
      roundedR = -roundedQ - roundedS;
    }
    return { q: roundedQ, r: roundedR };
  }

  function drawHexOutline(cx, cy) {
    ctx.beginPath();
    for (let i = 0; i < 6; i += 1) {
      const angle = Math.PI / 180 * (60 * i - 30);
      const x = cx + hexSize * Math.cos(angle);
      const y = cy + hexSize * Math.sin(angle);
      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.closePath();
    ctx.strokeStyle = "rgba(255, 253, 248, 0.8)";
    ctx.lineWidth = 3 / view.scale;
    ctx.stroke();
    ctx.strokeStyle = "rgba(23, 32, 28, 0.8)";
    ctx.lineWidth = 1 / view.scale;
    ctx.stroke();
  }

  function screenToWorld(clientX, clientY) {
    const rect = canvas.getBoundingClientRect();
    return {
      x: (clientX - rect.left - view.offsetX) / view.scale,
      y: (clientY - rect.top - view.offsetY) / view.scale,
    };
  }

  function draw() {
    const rect = canvas.getBoundingClientRect();
    ctx.clearRect(0, 0, rect.width, rect.height);
    ctx.save();
    ctx.translate(view.offsetX, view.offsetY);
    ctx.scale(view.scale, view.scale);

    if (mapImage.complete && mapImage.naturalWidth > 0) {
      ctx.drawImage(mapImage, 0, 0, mapWidth, mapHeight);
    } else {
      ctx.fillStyle = "#17201c";
      ctx.fillRect(0, 0, mapWidth, mapHeight);
    }

    ctx.restore();
    updateZoomReadout();
  }

  function fitMap() {
    const rect = canvas.getBoundingClientRect();
    view.scale = Math.min(rect.width / mapWidth, rect.height / mapHeight) * 0.92;
    view.offsetX = (rect.width - mapWidth * view.scale) / 2;
    view.offsetY = (rect.height - mapHeight * view.scale) / 2;
    draw();
  }

  function setZoom(nextScale) {
    view.scale = Math.min(Math.max(nextScale, 0.12), 2.4);
    draw();
  }

  function updateZoomReadout() {
    if (readouts.zoom) {
      readouts.zoom.textContent = `${Math.round(view.scale * 100)}%`;
    }
  }

  function updateHexReadout(event) {
    const point = screenToWorld(event.clientX, event.clientY);
    if (point.x < 0 || point.y < 0 || point.x > playableWidth || point.y > mapHeight) {
      readouts.hex.textContent = "none";
      draw();
      return;
    }
    const hex = pixelToHex(point.x, point.y);
    const center = hexToPixel(hex.q, hex.r);
    if (center.x < 0 || center.y < 0 || center.x > playableWidth || center.y > mapHeight) {
      readouts.hex.textContent = "none";
      draw();
      return;
    }
    readouts.hex.textContent = `${hex.q}, ${hex.r}`;
    draw();
    ctx.save();
    ctx.translate(view.offsetX, view.offsetY);
    ctx.scale(view.scale, view.scale);
    drawHexOutline(center.x, center.y);
    ctx.restore();
  }

  canvas.addEventListener("pointerdown", (event) => {
    drag.active = true;
    drag.x = event.clientX;
    drag.y = event.clientY;
    canvas.setPointerCapture(event.pointerId);
  });

  canvas.addEventListener("pointermove", (event) => {
    updateHexReadout(event);
    if (!drag.active) {
      return;
    }
    view.offsetX += event.clientX - drag.x;
    view.offsetY += event.clientY - drag.y;
    drag.x = event.clientX;
    drag.y = event.clientY;
    draw();
  });

  canvas.addEventListener("pointerup", (event) => {
    drag.active = false;
    canvas.releasePointerCapture(event.pointerId);
  });

  canvas.addEventListener("wheel", (event) => {
    event.preventDefault();
    const direction = event.deltaY > 0 ? -0.1 : 0.1;
    setZoom(view.scale + direction);
  }, { passive: false });

  shell.addEventListener("click", (event) => {
    const button = event.target.closest("[data-map-action]");
    if (!button) {
      return;
    }
    const action = button.dataset.mapAction;
    if (action === "fit") {
      fitMap();
    } else if (action === "zoom-in") {
      setZoom(view.scale + 0.15);
    } else if (action === "zoom-out") {
      setZoom(view.scale - 0.15);
    }
  });

  mapImage.addEventListener("load", () => {
    resizeCanvas();
    fitMap();
  });
  mapImage.src = shell.dataset.mapImage;

  window.addEventListener("resize", resizeCanvas);
  resizeCanvas();
}());
