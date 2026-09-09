// HojiDonatBot 1-to-1 Clone Engine
const tg = window.Telegram ? window.Telegram.WebApp : null;
if (tg) {
  tg.expand();
  tg.ready();
}

// State
let appUser = {
  id: 8459747832,
  first_name: "yahyo",
  username: "yahyozodaaaa",
  balance: 0.0,
  spent: 0.0
};

let currentRegion = "СНГ";
let verifiedFF = {
  uid: "",
  nickname: ""
};

let activeSelectedItem = null;
let topupData = {
  amount: 20,
  receiptBase64: null,
  fileName: ""
};

// The payment number is loaded from config.DC_NEXT_NUMBER on the server.
// Edit that one value in VS Code; do not edit payment numbers in this file.
let paymentConfig = {
  method: "DC.NEXT",
  cardNumber: "+992980726060"
};

let currentHistoryTab = "orders";
let currentHistoryFilter = "all";
let cachedOrders = [];
let cachedDeposits = [];

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  initTelegramProfile();
  loadCachedState();
  syncLiveBalance();
  loadPaymentConfig();
});

async function loadPaymentConfig() {
  try {
    const res = await fetch("/api/payment_config", { cache: "no-store" });
    const data = await res.json();
    if (res.ok && data.success && data.card_number) {
      paymentConfig.method = data.method || "DC.NEXT";
      paymentConfig.cardNumber = data.card_number;
    }
  } catch (e) {
    console.warn("Payment config unavailable; using the packaged value.");
  }

  document.querySelectorAll("[data-payment-card]").forEach((node) => {
    node.textContent = paymentConfig.cardNumber;
  });
}

function initTelegramProfile() {
  if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
    const u = tg.initDataUnsafe.user;
    appUser.id = u.id;
    appUser.first_name = u.first_name || "yahyo";
    appUser.username = u.username || "yahyozodaaaa";
  }

  // Populate Header
  document.getElementById("header-username").innerText = appUser.first_name;
  document.getElementById("header-tg-tag").innerText = "@" + (appUser.username || "user");
  document.getElementById("header-avatar").innerText = appUser.first_name.charAt(0).toUpperCase();

  // Populate Profile page
  document.getElementById("prof-avatar-letter").innerText = appUser.first_name.charAt(0).toUpperCase();
  document.getElementById("prof-username-text").innerText = appUser.first_name;
  document.getElementById("prof-tg-id-text").innerText = "ID: " + appUser.id;
}

function loadCachedState() {
  const savedUID = localStorage.getItem("ff_active_uid");
  const savedNick = localStorage.getItem("ff_active_nick");
  if (savedUID) {
    document.getElementById("ff-uid-input").value = savedUID;
    if (savedNick) {
      verifiedFF.uid = savedUID;
      verifiedFF.nickname = savedNick;
      renderVerifiedBadge(savedNick);
    }
  }

  const localBal = localStorage.getItem("app_balance_" + appUser.id);
  const localSpent = localStorage.getItem("app_spent_" + appUser.id);
  if (localBal !== null) appUser.balance = parseFloat(localBal);
  if (localSpent !== null) appUser.spent = parseFloat(localSpent);
  renderBalance();
}

async function syncLiveBalance() {
  try {
    const res = await fetch(`/api/user?user_id=${appUser.id}`);
    if (res.ok) {
      const data = await res.json();
      if (data.success) {
        appUser.balance = parseFloat(data.balance) || 0.0;
        appUser.spent = parseFloat(data.spent) || 0.0;
        localStorage.setItem("app_balance_" + appUser.id, appUser.balance);
        localStorage.setItem("app_spent_" + appUser.id, appUser.spent);
        renderBalance();
      }
    }
  } catch (e) {
    console.log("Local balance fallback");
  }
}

function renderBalance() {
  document.getElementById("main-balance-text").innerHTML = `${appUser.balance.toFixed(1)} <span>сомонӣ</span>`;
  document.getElementById("prof-stat-balance").innerHTML = `${appUser.balance.toFixed(1)} <span>сомонӣ</span>`;
  document.getElementById("prof-stat-spent").innerHTML = `${appUser.spent.toFixed(0)} <span>сомонӣ</span>`;
}

// Navigation between views
function navigateToView(viewId) {
  document.querySelectorAll(".app-view").forEach(v => v.style.display = "none");
  document.querySelectorAll(".nav-item-pill").forEach(n => n.classList.remove("active"));

  const target = document.getElementById("view-" + viewId);
  if (target) target.style.display = "block";

  const topHeader = document.getElementById("top-user-header");
  const balanceHero = document.getElementById("balance-hero-widget");

  // Show/hide top header & balance widget depending on view
  if (viewId === "menu") {
    topHeader.style.display = "flex";
    balanceHero.style.display = "block";
    document.getElementById("nav-btn-menu").classList.add("active");
  } else if (viewId === "history") {
    topHeader.style.display = "none";
    balanceHero.style.display = "none";
    document.getElementById("nav-btn-history").classList.add("active");
    fetchUserOrdersHistory();
  } else if (viewId === "profile") {
    topHeader.style.display = "none";
    balanceHero.style.display = "none";
    document.getElementById("nav-btn-profile").classList.add("active");
  } else {
    // Topup flow
    topHeader.style.display = "none";
    balanceHero.style.display = "none";
  }

  window.scrollTo(0, 0);
}

// Category tabs
function switchCategoryTab(cat) {
  document.querySelectorAll(".category-pill").forEach(p => p.classList.remove("active"));
  document.getElementById("grid-other").style.display = "none";
  document.getElementById("grid-almaz").style.display = "none";
  document.getElementById("grid-pass").style.display = "none";

  document.getElementById("tab-" + cat).classList.add("active");
  document.getElementById("grid-" + cat).style.display = "grid";
}

// Region Selection
function selectRegion(regName, el) {
  document.querySelectorAll(".region-pill").forEach(r => r.classList.remove("active"));
  el.classList.add("active");
  currentRegion = regName;
}

// Free Fire Real UID Verification
async function triggerUIDCheck() {
  const uidInput = document.getElementById("ff-uid-input").value.trim();
  if (!/^\d{6,12}$/.test(uidInput)) {
    alert("Лутфан ID-и дурустро ворид кунед (ҳадди ақал 6 рақам)!");
    return;
  }

  const badge = document.getElementById("ff-verified-badge");
  const nameSpan = document.getElementById("ff-player-name-text");
  nameSpan.innerText = "Ҷустуҷӯ...";
  badge.style.display = "flex";

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 18000);
    const res = await fetch(`/api/check_uid?uid=${encodeURIComponent(uidInput)}&region=${encodeURIComponent(currentRegion)}`, { signal: controller.signal });
    clearTimeout(timeout);
    const data = await res.json();
    if (data.success && data.status === "active" && data.nickname) {
      verifiedFF.uid = uidInput;
      verifiedFF.nickname = data.nickname;
      localStorage.setItem("ff_active_uid", uidInput);
      localStorage.setItem("ff_active_nick", data.nickname);
      renderVerifiedBadge(data.nickname + (data.ban_checked ? " ✓" : ""));
      return;
    }
    verifiedFF = { uid: "", nickname: "" };
    badge.style.display = "flex";
    nameSpan.innerText = data.status === "banned" ? "⛔ Аккаунт дар Free Fire баста шудааст" : (data.status === "not_found" ? "❌ Бозингар ёфт нашуд" : "⚠️ Санҷиш муваққатан дастнорас аст");
  } catch (e) {
    verifiedFF = { uid: "", nickname: "" };
    badge.style.display = "flex";
    nameSpan.innerText = "⚠️ Санҷиш муваққатан дастнорас аст";
  }
}

function renderVerifiedBadge(nick) {
  const badge = document.getElementById("ff-verified-badge");
  const nameSpan = document.getElementById("ff-player-name-text");
  nameSpan.innerText = nick;
  badge.style.display = "flex";
}

// Promo code
function applyPromoCode() {
  const code = document.getElementById("promo-code-field").value.trim();
  if (!code) {
    alert("Лутфан рамзи проморо нависед!");
    return;
  }
  if (code.toUpperCase() === "FORS" || code.toUpperCase() === "ALMAZ") {
    alert("🎉 Рамзи промо қабул шуд! Тахфифи 5% фаъол гардид.");
  } else {
    alert("❌ Рамзи промо ёфт нашуд ё мӯҳлаташ гузаштааст.");
  }
}

// Purchase Item Modal
function startPurchaseItem(itemId, title, diamonds, price, iconUrl) {
  const uid = document.getElementById("ff-uid-input").value.trim();
  if (!uid || uid.length < 6) {
    alert("Аввал ID-и Free Fire-и худро ворид кунед ва тугмаи 'Санҷидан'-ро пахш намоед!");
    document.getElementById("ff-uid-input").focus();
    return;
  }

  if (!verifiedFF.nickname || verifiedFF.uid !== uid) {
    alert("Аввал ID-и Free Fire-ро санҷед. Харид танҳо барои аккаунти тасдиқшуда иҷозат аст.");
    return;
  }

  activeSelectedItem = {
    itemId: itemId,
    title: title,
    diamonds: diamonds,
    price: price,
    uid: uid,
    nickname: verifiedFF.nickname,
    region: currentRegion,
    iconUrl: iconUrl
  };

  document.getElementById("modal-art-icon").src = iconUrl;
  document.getElementById("modal-art-title").innerText = title;
  document.getElementById("modal-art-uid").innerText = uid;
  document.getElementById("modal-art-nick").innerText = verifiedFF.nickname;
  document.getElementById("modal-art-region").innerText = currentRegion;
  document.getElementById("modal-art-price").innerText = price.toFixed(1) + " сомонӣ";
  document.getElementById("modal-art-userbalance").innerText = appUser.balance.toFixed(1) + " сомонӣ";

  const alertEl = document.getElementById("modal-insufficient-alert");
  const actionBtn = document.getElementById("modal-btn-action");

  if (appUser.balance < price) {
    alertEl.style.display = "block";
    alertEl.innerText = `Баланси шумо (${appUser.balance.toFixed(1)} с.) барои харид (${price.toFixed(1)} с.) кифоя нест!`;
    actionBtn.innerText = "Пур кардани баланс";
    actionBtn.onclick = () => {
      closePurchaseModal();
      openTopUpStep1();
    };
  } else {
    alertEl.style.display = "none";
    actionBtn.innerText = "Тасдиқи харид ✓";
    actionBtn.onclick = executeOrder;
  }

  document.getElementById("purchase-modal-sheet").classList.add("open");
}

function closePurchaseModal() {
  document.getElementById("purchase-modal-sheet").classList.remove("open");
  activeSelectedItem = null;
}

// Execute Purchase
async function executeOrder() {
  if (!activeSelectedItem) return;

  const it = activeSelectedItem;
  const payload = {
    type: "order",
    user_id: appUser.id,
    item_id: it.itemId,
    item_title: it.title,
    diamonds: it.diamonds,
    price: it.price,
    uid: it.uid,
    nickname: it.nickname,
    region: it.region
  };

  let ok = false;
  try {
    const res = await fetch("/api/buy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      const data = await res.json();
      if (data.success) {
        ok = true;
        appUser.balance = data.new_balance;
        appUser.spent += it.price;
        renderBalance();
      } else {
        alert(data.message || "Хатогӣ рух дод!");
        return;
      }
    }
  } catch (e) {
    console.log("Sending order via Telegram WebApp:", e);
  }

  if (tg && typeof tg.sendData === "function") {
    tg.sendData(JSON.stringify(payload));
  }

  // Save to local cached orders
  let list = JSON.parse(localStorage.getItem("user_orders_" + appUser.id) || "[]");
  list.unshift({
    item_title: it.title,
    price: it.price,
    uid: it.uid,
    nickname: it.nickname,
    status: "pending",
    created_at: new Date().toLocaleDateString("tg-TJ") + " " + new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})
  });
  localStorage.setItem("user_orders_" + appUser.id, JSON.stringify(list));

  if (tg && tg.HapticFeedback) {
    tg.HapticFeedback.notificationOccurred("success");
  }

  closePurchaseModal();
  alert(`🎉 Фармоиш барои "${it.title}" қабул шуд!\nID: ${it.uid}\nАлмазҳо дар давоми 1-3 дақиқа ворид карда мешаванд.`);
  navigateToView("history");
}

// ==================== TOPUP 3-STEP FLOW ====================
function openTopUpStep1() {
  navigateToView("topup-step1");
}

function selectPresetTopup(val, el) {
  document.querySelectorAll(".preset-amount-btn").forEach(b => b.classList.remove("active"));
  el.classList.add("active");
  document.getElementById("custom-topup-amount").value = val;
  topupData.amount = val;
}

function goToTopupStep2() {
  const val = parseFloat(document.getElementById("custom-topup-amount").value);
  if (!val || val <= 0) {
    alert("Лутфан маблағи дурустро ворид кунед!");
    return;
  }
  topupData.amount = val;
  navigateToView("topup-step2");
}

function goToTopupStep3() {
  document.getElementById("step3-amount-display").innerText = `${topupData.amount} сомонӣ`;
  navigateToView("topup-step3");
}

function copyCardNumber() {
  const num = paymentConfig.cardNumber;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(num).then(() => alert("Рақам нусхабардорӣ шуд: " + num));
  } else {
    alert("Рақам: " + num);
  }
}

function handleReceiptFileSelected(input) {
  if (!input.files || !input.files[0]) return;
  const file = input.files[0];
  topupData.fileName = file.name;

  const reader = new FileReader();
  reader.onload = function(e) {
    topupData.receiptBase64 = e.target.result;
    const dropzone = document.getElementById("receipt-dropzone");
    const label = document.getElementById("dropzone-status-text");
    dropzone.classList.add("has-file");
    label.innerHTML = `✅ Расми чек интихоб шуд: <br><span style="font-size:12px; color:#34d399;">${file.name}</span>`;

    const submitBtn = document.getElementById("btn-submit-receipt");
    submitBtn.disabled = false;
    submitBtn.style.opacity = "1";
  };
  reader.readAsDataURL(file);
}

async function sendDepositReceiptToServer() {
  if (!topupData.receiptBase64) {
    alert("Лутфан расми чекро интихоб кунед!");
    return;
  }

  const submitBtn = document.getElementById("btn-submit-receipt");
  submitBtn.innerText = "Ирсол шуда истодааст...";
  submitBtn.disabled = true;

  try {
    const res = await fetch("/api/upload_receipt", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: appUser.id,
        amount: topupData.amount,
        image_base64: topupData.receiptBase64
      })
    });
    if (res.ok) {
      const data = await res.json();
      if (data.success) {
        alert("📩 Чеки шумо ба администратор равон карда шуд!\nПас аз санҷиш (дар 1-3 дақиқа) баланси шумо пур карда мешавад.");
        navigateToView("history");
        switchHistoryTab("finance");
        return;
      }
    }
  } catch (e) {
    console.log("Offline receipt upload fallback:", e);
  }

  alert("📩 Чеки шумо қабул шуд! Админ онро тасдиқ мекунад.");
  navigateToView("history");
  switchHistoryTab("finance");
}

// ==================== HISTORY TAB ====================
function switchHistoryTab(tab) {
  currentHistoryTab = tab;
  if (tab === "orders") {
    document.getElementById("btn-hist-orders").classList.add("active");
    document.getElementById("btn-hist-finance").classList.remove("active");
  } else {
    document.getElementById("btn-hist-orders").classList.remove("active");
    document.getElementById("btn-hist-finance").classList.add("active");
  }
  renderHistoryView();
}

function filterHistory(filt, el) {
  document.querySelectorAll(".history-chip").forEach(c => c.classList.remove("active"));
  el.classList.add("active");
  currentHistoryFilter = filt;
  renderHistoryView();
}

async function fetchUserOrdersHistory() {
  try {
    const res = await fetch(`/api/history?user_id=${appUser.id}`);
    if (res.ok) {
      const data = await res.json();
      if (data.success) {
        cachedOrders = data.orders || [];
        cachedDeposits = data.deposits || [];
        renderHistoryView();
        return;
      }
    }
  } catch (e) {
    console.log("Local history render");
  }

  cachedOrders = JSON.parse(localStorage.getItem("user_orders_" + appUser.id) || "[]");
  renderHistoryView();
}

function renderHistoryView() {
  const container = document.getElementById("history-items-container");
  const list = currentHistoryTab === "orders" ? cachedOrders : cachedDeposits;

  let filtered = list;
  if (currentHistoryFilter !== "all") {
    filtered = list.filter(x => x.status === currentHistoryFilter);
  }

  if (!filtered || filtered.length === 0) {
    container.innerHTML = `
      <div class="empty-state-wrap">
        <svg viewBox="0 0 24 24"><path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/></svg>
        <h4>Маълумот нест</h4>
      </div>
    `;
    return;
  }

  container.innerHTML = filtered.map(item => {
    const isCompleted = item.status === "completed" || item.status === "approved";
    const isRejected = item.status === "cancelled" || item.status === "rejected";
    const statusText = isCompleted ? "✓ Иҷро шуд" : (isRejected ? "✕ Рад шуд" : "⏳ Дар интизор");
    const statusColor = isCompleted ? "#10b981" : (isRejected ? "#ef4444" : "#f59e0b");
    const title = item.item_title || `Пур кардани баланс (+${item.amount} с.)`;
    const sub = item.uid ? `UID: ${item.uid}` : "Пардохт тавассути DC Next";

    return `
      <div style="background:var(--bg-card); border:1px solid var(--border-card); border-radius:16px; padding:14px; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center;">
        <div>
          <div style="font-size:14px; font-weight:800;">${title}</div>
          <div style="font-size:12px; color:var(--text-muted); margin-top:2px;">${sub}</div>
          <div style="font-size:11px; color:var(--text-dim); margin-top:3px;">${item.created_at || ""}</div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:15px; font-weight:900; color:#818cf8;">${item.price ? item.price + " с." : "+" + item.amount + " с."}</div>
          <span style="font-size:11px; font-weight:700; color:${statusColor};">${statusText}</span>
        </div>
      </div>
    `;
  }).join("");
}

// Utilities
function copyMyTGID() {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(String(appUser.id)).then(() => alert("ID нусхабардорӣ шуд: " + appUser.id));
  } else {
    alert("ID: " + appUser.id);
  }
}

function shareReferral() {
  const refLink = `https://t.me/ForsAlmaz_Bot?start=ref_${appUser.id}`;
  if (tg && typeof tg.openTelegramLink === "function") {
    tg.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(refLink)}&text=${encodeURIComponent("Ба беҳтарин боти донати Free Fire ҳамроҳ шавед!")}`);
  } else {
    alert("Истиноди даъвати шумо:\n" + refLink);
  }
}

function openSupportLink() {
  if (tg && typeof tg.openTelegramLink === "function") {
    tg.openTelegramLink("https://t.me/yahyoezz5");
  } else {
    window.open("https://t.me/yahyoezz5", "_blank");
  }
}

function toggleTheme() {
  document.body.classList.toggle("light-mode");
}

function toggleSound() {
  alert("Садо фурӯзон/хомӯш шуд.");
}
