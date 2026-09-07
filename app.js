const state = {
  session: null,
  currentFilter: 'all',
  messages: [],
  selectedMessageId: null,
  selectedRecipientAddress: null,
  selectedMessageIds: [],
  selectionAnchorMessageId: null,
  selectedMessageCache: null,
  messageTranslations: {},
  messageTranslationVisibility: {},
  mainSearch: '',
  recentMessageIds: {},
  seenMessageIds: {},
  hasLoadedMessages: false,
  currentPage: 1,
  composeDraft: null,
  messageListSignature: '',
  currentView: 'mail',
  users: [],
  editingUserId: null,
  excludedAliases: [],
  forwardingRules: [],
  forwardingSearch: '',
  editingForwardingRuleId: null,
  newMessageAttachments: [],
  senderAliases: [],
  detailPaneWidth: null,
};

const dom = {};
let mainSearchTimer = null;
let autoRefreshTimer = null;
let refreshPromise = null;
let relativeTimeTimer = null;
let adminEventsSource = null;
let adminEventReconnectTimer = null;
let adminEventVersion = 0;
let detailResizeActive = false;
let detailResizeStartX = 0;
let detailResizeStartWidth = 0;

const AUTO_VIEW_REFRESH_MS = 15000;
const RELATIVE_TIME_REFRESH_MS = 10000;
const STREAM_RECONNECT_DELAY_MS = 2500;
const NEW_MESSAGE_HIGHLIGHT_MS = 180000;
const MESSAGES_PER_PAGE = 12;
const DETAIL_WIDTH_STORAGE_KEY = 'darkambient.detailPaneWidth';
const DETAIL_DEFAULT_WIDTH = 420;
const DETAIL_MIN_WIDTH = 360;
const DETAIL_MAX_WIDTH = 760;
const MAIL_LIST_MIN_WIDTH = 420;
const MAX_ATTACHMENT_COUNT = 10;
const MAX_ATTACHMENT_TOTAL_BYTES = 18 * 1024 * 1024;
const AVATAR_PALETTES = [
  { background: 'linear-gradient(135deg, #14b8a6 0%, #0f766e 100%)', color: '#f0fdfa' },
  { background: 'linear-gradient(135deg, #2dd4bf 0%, #0d9488 100%)', color: '#f0fdfa' },
  { background: 'linear-gradient(135deg, #fb7185 0%, #e11d48 100%)', color: '#fff1f2' },
  { background: 'linear-gradient(135deg, #38bdf8 0%, #2563eb 100%)', color: '#eff6ff' },
  { background: 'linear-gradient(135deg, #34d399 0%, #059669 100%)', color: '#ecfdf5' },
  { background: 'linear-gradient(135deg, #a78bfa 0%, #7c3aed 100%)', color: '#f5f3ff' },
];

document.addEventListener('DOMContentLoaded', async () => {
  cacheDom();
  initDetailPaneWidth();
  bindEvents();
  lucide.createIcons();
  await bootstrapSession();
});

function cacheDom() {
  const ids = [
    'loginPage', 'appPage', 'loginForm', 'loginEmail', 'loginPassword', 'loginError', 'logoutBtn',
    'mailNav', 'folderTitle', 'folderCount', 'emailList', 'emptyState', 'detailContent',
    'mobileDetail', 'mobileDetailContent', 'sidebar', 'sidebarOverlay', 'sidebarToggle',
    'closeSidebarBtn', 'mainSearch', 'deleteAllBtn', 'newMessageBtn', 'toast',
    'toastMsg', 'closeMobileDetailBtn', 'paginationInfo', 'paginationControls',
    'mailView', 'usersView', 'autoDeleteView', 'forwardingView', 'usersTabBtn', 'autoDeleteTabBtn',
    'forwardingTabBtn',
    'userCount', 'userList', 'userEmptyState',
    'createUserBtn', 'userModal', 'userForm', 'userModalTitle', 'userUsernameInput',
    'userPasswordInput', 'userPasswordHint', 'userRoleInput', 'userFormError',
    'closeUserModalBtn', 'cancelUserFormBtn', 'saveUserBtn', 'emailDetail',
    'detailResizeHandle',
    'autoDeleteCount', 'autoDeleteForm', 'autoDeleteAddressInput', 'autoDeleteReasonInput',
    'saveAutoDeleteBtn', 'autoDeleteList', 'autoDeleteEmptyState',
    'forwardingCount', 'forwardingForm', 'forwardingSourceInput', 'forwardingTargetInput',
    'saveForwardingBtn', 'forwardingList', 'forwardingEmptyState', 'forwardingSearchInput',
    'forwardingEditModal', 'forwardingEditForm', 'forwardingEditSourceInput',
    'forwardingEditTargetInput', 'forwardingEditError', 'closeForwardingEditBtn',
    'cancelForwardingEditBtn', 'saveForwardingEditBtn',
    'newMessageModal', 'newMessageForm', 'newMessageFrom', 'senderAliasOptions', 'newMessageTo', 'newMessageCc',
    'newMessageSubject', 'newMessageBody', 'newMessageError', 'closeNewMessageBtn',
    'cancelNewMessageBtn', 'sendNewMessageBtn', 'newMessageAttachmentInput',
    'newMessageAttachmentBtn', 'newMessageAttachmentCount', 'newMessageAttachmentList',
  ];
  ids.forEach((id) => { dom[id] = document.getElementById(id); });
}

function bindEvents() {
  dom.loginForm.addEventListener('submit', onLoginSubmit);
  dom.logoutBtn.addEventListener('click', logout);
  dom.sidebarToggle.addEventListener('click', openSidebar);
  dom.closeSidebarBtn.addEventListener('click', closeSidebar);
  dom.sidebarOverlay.addEventListener('click', closeSidebar);
  dom.deleteAllBtn.addEventListener('click', () => deleteAllMessagesInScope().catch(handleError));
  dom.newMessageBtn.addEventListener('click', () => openNewMessageComposer().catch(handleError));
  dom.mainSearch.addEventListener('input', onMainSearchChange);
  dom.closeMobileDetailBtn.addEventListener('click', closeMobileDetail);
  dom.usersTabBtn.addEventListener('click', () => setAdminView('users'));
  dom.autoDeleteTabBtn.addEventListener('click', () => setAdminView('auto-delete'));
  dom.forwardingTabBtn.addEventListener('click', () => setAdminView('forwarding'));
  dom.forwardingSearchInput.addEventListener('input', onForwardingSearchChange);
  dom.createUserBtn.addEventListener('click', openCreateUserModal);
  dom.autoDeleteForm.addEventListener('submit', onAutoDeleteFormSubmit);
  dom.forwardingForm.addEventListener('submit', onForwardingFormSubmit);
  dom.forwardingEditForm.addEventListener('submit', onForwardingEditSubmit);
  dom.userForm.addEventListener('submit', onUserFormSubmit);
  dom.closeUserModalBtn.addEventListener('click', closeUserModal);
  dom.cancelUserFormBtn.addEventListener('click', closeUserModal);
  dom.newMessageForm.addEventListener('submit', sendNewMessage);
  dom.closeNewMessageBtn.addEventListener('click', closeNewMessageComposer);
  dom.cancelNewMessageBtn.addEventListener('click', closeNewMessageComposer);
  dom.closeForwardingEditBtn.addEventListener('click', closeForwardingEditModal);
  dom.cancelForwardingEditBtn.addEventListener('click', closeForwardingEditModal);
  dom.newMessageAttachmentBtn.addEventListener('click', () => dom.newMessageAttachmentInput.click());
  dom.newMessageAttachmentInput.addEventListener('change', onNewMessageAttachmentChange);
  dom.newMessageModal.addEventListener('click', (event) => {
    if (event.target instanceof HTMLElement && event.target.dataset.newMessageClose === 'true') {
      closeNewMessageComposer();
    }
  });
  dom.userModal.addEventListener('click', (event) => {
    if (event.target instanceof HTMLElement && event.target.dataset.userModalClose === 'true') {
      closeUserModal();
    }
  });
  dom.forwardingEditModal.addEventListener('click', (event) => {
    if (event.target instanceof HTMLElement && event.target.dataset.forwardingEditClose === 'true') {
      closeForwardingEditModal();
    }
  });

  document.querySelectorAll('#mailNav .folder-btn').forEach((button) => {
    if (button.dataset.filter) {
      button.addEventListener('click', () => setMailFilter(button.dataset.filter));
    }
  });

  document.addEventListener('click', onDocumentClick);
  document.addEventListener('keydown', onGlobalKeyDown);
  document.addEventListener('visibilitychange', onVisibilityChange);
  window.addEventListener('resize', onWindowResize);
  dom.detailResizeHandle.addEventListener('pointerdown', onDetailResizePointerDown);
  dom.detailResizeHandle.addEventListener('keydown', onDetailResizeKeyDown);
}

function onDocumentClick(event) {
  if (state.selectedMessageIds.length <= 1) {
    return;
  }
  if (!(event.target instanceof HTMLElement)) {
    return;
  }
  if (event.target.closest('[data-message-id]')) {
    return;
  }

  clearSelection();
}

function onGlobalKeyDown(event) {
  if (event.key === 'Escape' && !dom.newMessageModal.classList.contains('hidden')) {
    event.preventDefault();
    closeNewMessageComposer();
    return;
  }
  if (isEditableTarget(event.target)) {
    return;
  }
  if (state.currentView !== 'mail') {
    return;
  }

  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'a') {
    event.preventDefault();
    selectAllVisibleMessages().catch(handleError);
    return;
  }

  if (event.key !== 'Delete' || event.repeat) {
    return;
  }

  const targetIds = getVisibleSelectedMessageIds();
  if (!targetIds.length) {
    return;
  }

  event.preventDefault();
  deleteMessages(targetIds);
}

function isEditableTarget(target) {
  if (!(target instanceof HTMLElement)) {
    return false;
  }
  return Boolean(target.closest('input, textarea, [contenteditable="true"], [contenteditable=""], select'));
}

function clearSelection() {
  state.selectedMessageId = null;
  state.selectedRecipientAddress = null;
  state.selectedMessageIds = [];
  state.selectionAnchorMessageId = null;
  state.selectedMessageCache = null;
  state.composeDraft = null;
  renderMessages();
  resetDetail();
}

async function bootstrapSession() {
  try {
    const payload = await api('/api/auth/session');
    state.session = payload.user;
    if (state.session.role === 'user') {
      window.location.replace('/user.html');
      return;
    }
    showApp();
    startAdminEventStream();
    await refreshData({ silent: true, forceSync: false });
    refreshData({ silent: true, forceSync: true }).catch(handleError);
    restartAutoRefresh();
    restartRelativeTimeTicker();
  } catch {
    showLogin();
  }
}

async function onLoginSubmit(event) {
  event.preventDefault();
  dom.loginError.classList.add('hidden');
  try {
    const payload = await api('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        username: dom.loginEmail.value.trim(),
        password: dom.loginPassword.value,
      }),
    });
    state.session = payload.user;
    if (state.session.role === 'user') {
      window.location.replace('/user.html');
      return;
    }
    showApp();
    startAdminEventStream();
    await refreshData({ silent: true, forceSync: false });
    refreshData({ silent: true, forceSync: true }).catch(handleError);
    restartAutoRefresh();
    restartRelativeTimeTicker();
    showToast('Đăng nhập thành công');
  } catch (error) {
    dom.loginError.textContent = error.message || 'Đăng nhập thất bại';
    dom.loginError.classList.remove('hidden');
  }
}

async function logout() {
  try {
    await api('/api/auth/logout', { method: 'POST' });
  } catch {
    // Ignore logout network errors and clear UI anyway.
  }
  state.session = null;
  state.messages = [];
  state.selectedMessageId = null;
  state.selectedRecipientAddress = null;
  state.selectedMessageIds = [];
  state.selectionAnchorMessageId = null;
  state.selectedMessageCache = null;
  state.messageTranslations = {};
  state.messageTranslationVisibility = {};
  state.recentMessageIds = {};
  state.seenMessageIds = {};
  state.hasLoadedMessages = false;
  state.currentPage = 1;
  state.composeDraft = null;
  state.messageListSignature = '';
  state.currentView = 'mail';
  state.users = [];
  state.editingUserId = null;
  state.excludedAliases = [];
  state.forwardingRules = [];
  state.forwardingSearch = '';
  state.editingForwardingRuleId = null;
  state.newMessageAttachments = [];
  stopAutoRefresh();
  stopRelativeTimeTicker();
  stopAdminEventStream();
  showLogin();
}

function showLogin() {
  dom.appPage.classList.add('hidden');
  dom.loginPage.classList.remove('hidden');
  dom.loginPassword.value = '';
  stopAutoRefresh();
  stopRelativeTimeTicker();
  stopAdminEventStream();
  closeSidebar();
  resetDetail();
  lucide.createIcons();
}

function showApp() {
  dom.loginPage.classList.add('hidden');
  dom.appPage.classList.remove('hidden');
  setAdminView('mail');
  lucide.createIcons();
}

function onVisibilityChange() {
  if (!state.session) {
    return;
  }
  if (document.visibilityState === 'visible') {
    startAdminEventStream();
    refreshData({ silent: true, forceSync: false }).catch(handleError);
    restartAutoRefresh();
    restartRelativeTimeTicker();
    return;
  }
  stopAutoRefresh();
  stopRelativeTimeTicker();
  stopAdminEventStream();
}

function restartAutoRefresh() {
  stopAutoRefresh();
  if (!state.session || document.visibilityState !== 'visible') {
    return;
  }
  autoRefreshTimer = window.setInterval(() => {
    refreshData({ silent: true, forceSync: false }).catch(handleError);
  }, AUTO_VIEW_REFRESH_MS);
}

function stopAutoRefresh() {
  if (!autoRefreshTimer) {
    return;
  }
  window.clearInterval(autoRefreshTimer);
  autoRefreshTimer = null;
}

function startAdminEventStream() {
  stopAdminEventStream();
  if (!state.session || state.session.role !== 'admin' || document.visibilityState !== 'visible' || typeof EventSource === 'undefined') {
    return;
  }

  adminEventsSource = new EventSource('/api/events', { withCredentials: true });
  adminEventsSource.addEventListener('ready', handleAdminEvent);
  adminEventsSource.addEventListener('heartbeat', handleAdminEvent);
  adminEventsSource.addEventListener('messages', handleAdminEvent);
  adminEventsSource.onerror = () => {
    scheduleAdminEventReconnect();
  };
}

function stopAdminEventStream() {
  if (adminEventsSource) {
    adminEventsSource.close();
    adminEventsSource = null;
  }
  if (adminEventReconnectTimer) {
    window.clearTimeout(adminEventReconnectTimer);
    adminEventReconnectTimer = null;
  }
}

function scheduleAdminEventReconnect() {
  if (adminEventReconnectTimer || !state.session || state.session.role !== 'admin' || document.visibilityState !== 'visible') {
    return;
  }
  stopAdminEventStream();
  adminEventReconnectTimer = window.setTimeout(() => {
    adminEventReconnectTimer = null;
    startAdminEventStream();
  }, STREAM_RECONNECT_DELAY_MS);
}

function handleAdminEvent(event) {
  let payload;
  try {
    payload = JSON.parse(event.data || '{}');
  } catch {
    return;
  }

  if (typeof payload.version === 'number' && payload.version > adminEventVersion) {
    adminEventVersion = payload.version;
  }

  if (event.type !== 'messages' || document.visibilityState !== 'visible') {
    return;
  }

  refreshData({ silent: true, forceSync: false }).catch(handleError);
}

function restartRelativeTimeTicker() {
  stopRelativeTimeTicker();
  if (!state.session) {
    return;
  }
  relativeTimeTimer = window.setInterval(() => {
    refreshRelativeTimeLabels();
  }, RELATIVE_TIME_REFRESH_MS);
}

function stopRelativeTimeTicker() {
  if (!relativeTimeTimer) {
    return;
  }
  window.clearInterval(relativeTimeTimer);
  relativeTimeTimer = null;
}

function openSidebar() {
  dom.sidebar.classList.remove('-translate-x-full');
  dom.sidebarOverlay.classList.remove('hidden');
}

function closeSidebar() {
  dom.sidebar.classList.add('-translate-x-full');
  dom.sidebarOverlay.classList.add('hidden');
}

function initDetailPaneWidth() {
  const savedWidth = readStoredDetailPaneWidth();
  applyDetailPaneWidth(savedWidth || getDefaultDetailPaneWidth(), { persist: false });
}

function readStoredDetailPaneWidth() {
  try {
    const value = Number.parseInt(localStorage.getItem(DETAIL_WIDTH_STORAGE_KEY) || '', 10);
    return Number.isFinite(value) ? value : null;
  } catch {
    return null;
  }
}

function getDetailWidthBounds() {
  const containerWidth = dom.emailDetail?.parentElement?.getBoundingClientRect().width || window.innerWidth;
  const maxFromLayout = Math.max(DETAIL_MIN_WIDTH, containerWidth - MAIL_LIST_MIN_WIDTH);
  return {
    min: DETAIL_MIN_WIDTH,
    max: Math.max(DETAIL_MIN_WIDTH, Math.min(DETAIL_MAX_WIDTH, maxFromLayout)),
  };
}

function getDefaultDetailPaneWidth() {
  return Math.max(DETAIL_DEFAULT_WIDTH, Math.round((window.innerWidth * 0.5) - 380));
}

function clampDetailPaneWidth(width) {
  const bounds = getDetailWidthBounds();
  return Math.min(bounds.max, Math.max(bounds.min, Math.round(width)));
}

function applyDetailPaneWidth(width, options = {}) {
  const { persist = true } = options;
  const nextWidth = clampDetailPaneWidth(width);
  state.detailPaneWidth = nextWidth;
  document.documentElement.style.setProperty('--mail-detail-width', `${nextWidth}px`);
  if (persist) {
    try {
      localStorage.setItem(DETAIL_WIDTH_STORAGE_KEY, String(nextWidth));
    } catch {
      // Ignore storage failures; resizing should still work for the current page.
    }
  }
}

function onDetailResizePointerDown(event) {
  if (window.innerWidth < 1024 || event.button !== 0) {
    return;
  }
  event.preventDefault();
  detailResizeActive = true;
  detailResizeStartX = event.clientX;
  detailResizeStartWidth = dom.emailDetail?.getBoundingClientRect().width || state.detailPaneWidth || DETAIL_DEFAULT_WIDTH;
  document.body.classList.add('detail-resizing');
  dom.detailResizeHandle.setPointerCapture?.(event.pointerId);
  document.addEventListener('pointermove', onDetailResizePointerMove);
  document.addEventListener('pointerup', onDetailResizePointerUp, { once: true });
  document.addEventListener('pointercancel', onDetailResizePointerUp, { once: true });
}

function onDetailResizePointerMove(event) {
  if (!detailResizeActive) {
    return;
  }
  event.preventDefault();
  applyDetailPaneWidth(detailResizeStartWidth + detailResizeStartX - event.clientX);
}

function onDetailResizePointerUp() {
  detailResizeActive = false;
  detailResizeStartX = 0;
  detailResizeStartWidth = 0;
  document.body.classList.remove('detail-resizing');
  document.removeEventListener('pointermove', onDetailResizePointerMove);
  document.removeEventListener('pointercancel', onDetailResizePointerUp);
}

function onDetailResizeKeyDown(event) {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
    return;
  }
  event.preventDefault();
  const currentWidth = state.detailPaneWidth || DETAIL_DEFAULT_WIDTH;
  if (event.key === 'Home') {
    applyDetailPaneWidth(DETAIL_MIN_WIDTH);
    return;
  }
  if (event.key === 'End') {
    applyDetailPaneWidth(DETAIL_MAX_WIDTH);
    return;
  }
  const delta = event.shiftKey ? 48 : 24;
  applyDetailPaneWidth(currentWidth + (event.key === 'ArrowLeft' ? delta : -delta));
}

function onWindowResize() {
  applyDetailPaneWidth(state.detailPaneWidth || getDefaultDetailPaneWidth(), { persist: false });
}

function setAdminView(viewName) {
  const nextView = ['users', 'auto-delete', 'forwarding'].includes(viewName) ? viewName : 'mail';
  state.currentView = nextView;
  dom.appPage.classList.toggle('users-mode', nextView !== 'mail');
  dom.mailView.classList.toggle('hidden', nextView !== 'mail');
  dom.mailView.classList.toggle('flex', nextView === 'mail');
  dom.usersView.classList.toggle('hidden', nextView !== 'users');
  dom.usersView.classList.toggle('flex', nextView === 'users');
  dom.autoDeleteView.classList.toggle('hidden', nextView !== 'auto-delete');
  dom.autoDeleteView.classList.toggle('flex', nextView === 'auto-delete');
  dom.forwardingView.classList.toggle('hidden', nextView !== 'forwarding');
  dom.forwardingView.classList.toggle('flex', nextView === 'forwarding');
  document.querySelectorAll('#mailNav .folder-btn').forEach((button) => {
    if (button.dataset.filter) {
      button.classList.toggle('active', nextView === 'mail' && button.dataset.filter === state.currentFilter);
    }
  });
  dom.usersTabBtn.classList.toggle('active', nextView === 'users');
  dom.autoDeleteTabBtn.classList.toggle('active', nextView === 'auto-delete');
  dom.forwardingTabBtn.classList.toggle('active', nextView === 'forwarding');
  if (nextView === 'users') {
    closeMobileDetail();
    resetDetail();
    loadUsers().catch(handleError);
  }
  if (nextView === 'auto-delete') {
    closeMobileDetail();
    resetDetail();
    loadExcludedAliases().catch(handleError);
  }
  if (nextView === 'forwarding') {
    closeMobileDetail();
    resetDetail();
    loadForwardingRules().catch(handleError);
  }
  closeSidebar();
  lucide.createIcons();
}

function setMailFilter(filterName) {
  setAdminView('mail');
  if (state.currentFilter === filterName) {
    return;
  }
  state.currentFilter = filterName;
  state.currentPage = 1;
  state.selectedMessageId = null;
  state.selectedRecipientAddress = null;
  state.selectedMessageIds = [];
  state.selectionAnchorMessageId = null;
  state.selectedMessageCache = null;
  state.composeDraft = null;
  resetDetail();
  document.querySelectorAll('#mailNav .folder-btn').forEach((button) => {
    button.classList.toggle('active', button.dataset.filter === filterName);
  });
  loadMessages({ preserveDetail: true }).catch(handleError);
}

async function refreshData(options = {}) {
  const { silent = false, forceSync = true } = options;
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    try {
      let syncPayload = null;
      if (forceSync) {
        syncPayload = await api('/api/sync', { method: 'POST' });
      }
      await loadDashboard({ preserveDetail: true });
      if (!silent && syncPayload) {
        showToast(syncPayload.synced ? `Đã đồng bộ ${syncPayload.synced} email mới` : 'Không có email mới');
      }
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

function refreshRelativeTimeLabels() {
  if (!state.session || document.visibilityState !== 'visible') {
    return;
  }

  document.querySelectorAll('[data-relative-time]').forEach((node) => {
    node.textContent = formatRelativeDate(node.dataset.relativeTime);
  });

  pruneRecentMessageIds();
  updateRecentMessageDecorations();
}

async function loadDashboard(options = {}) {
  const { preserveDetail = false } = options;
  await loadMessages({ preserveDetail });

  if (!preserveDetail || (!state.selectedMessageId && !state.selectedMessageCache)) {
    resetDetail();
  }
}

async function loadMessages(options = {}) {
  const { preserveDetail = false } = options;
  const previousSignature = state.messageListSignature;
  const previousPage = state.currentPage;
  const previousSelectedMessageId = state.selectedMessageId;
  const previousSelectedRecipientAddress = state.selectedRecipientAddress;
  const params = getMessageQueryParams();

  const endpoint = isSentFolder() ? '/api/sent-messages' : '/api/messages';
  const payload = await api(`${endpoint}?${params.toString()}`);
  markRecentMessages(payload.items);
  state.messages = payload.items;
  state.selectedMessageIds = state.selectedMessageIds.filter((id) => state.messages.some((item) => item.id === id));

  if (state.selectedMessageId && !state.messages.some((item) => (
    item.id === state.selectedMessageId
    && (isSentMessage(item) || item.recipient_address === state.selectedRecipientAddress)
  ))) {
    state.selectedMessageId = null;
    state.selectedRecipientAddress = null;
    state.selectedMessageCache = null;
    state.composeDraft = null;
  }
  if (state.selectedMessageId && !state.selectedMessageIds.includes(state.selectedMessageId)) {
    state.selectedMessageIds = [state.selectedMessageId];
  }
  if (!state.selectedMessageId && !state.selectedMessageIds.length) {
    state.selectionAnchorMessageId = null;
  }

  const nextSignature = buildMessageListSignature(state.messages);
  ensureValidPage();
  const pageChanged = state.currentPage !== previousPage;
  const selectionChanged = state.selectedMessageId !== previousSelectedMessageId
    || state.selectedRecipientAddress !== previousSelectedRecipientAddress;
  const shouldRenderList = nextSignature !== previousSignature || pageChanged || selectionChanged;

  if (shouldRenderList) {
    state.messageListSignature = nextSignature;
    renderMessages();
  } else {
    updateRecentMessageDecorations();
  }

  updateHeader();
  if (shouldRenderList || pageChanged) {
    renderPagination();
  }

  if (!state.selectedMessageId) {
    resetDetail();
  } else if (!preserveDetail && state.selectedMessageCache) {
    renderDetail(state.selectedMessageCache);
  }

  state.hasLoadedMessages = true;
}

function getMessageQueryParams() {
  const params = new URLSearchParams();
  if (!isSentFolder()) {
    params.set('filter_name', state.currentFilter);
  }
  if (state.mainSearch.trim()) {
    params.set('search', state.mainSearch.trim());
  }
  return params;
}

function onMainSearchChange(event) {
  clearTimeout(mainSearchTimer);
  state.mainSearch = event.target.value;
  state.currentPage = 1;
  mainSearchTimer = setTimeout(() => {
    loadMessages({ preserveDetail: true }).catch(handleError);
  }, 180);
}

function renderMessages() {
  const visibleMessages = getVisibleMessages();

  if (!state.messages.length) {
    dom.emailList.innerHTML = '';
    dom.emailList.classList.add('hidden');
    dom.emptyState.classList.remove('hidden');
    dom.emptyState.classList.add('flex');
    lucide.createIcons();
    return;
  }

  dom.emailList.classList.remove('hidden');
  dom.emptyState.classList.add('hidden');
  dom.emptyState.classList.remove('flex');

  dom.emailList.innerHTML = visibleMessages.map((message) => {
    if (isSentMessage(message)) {
      return renderSentMessageRow(message);
    }

    const selectedCls = isMessageSelected(message.id, message.recipient_address) ? 'selected' : '';
    const unreadCls = message.unread ? 'unread' : '';
    const recentCls = isRecentMessage(message.id) ? 'recent' : '';
    const hasOtp = Boolean(message.has_otps || message.extracted_otps?.length);
    const hasLinks = Boolean(message.has_links || message.extracted_links?.length);
    const newBadge = isRecentMessage(message.id) ? '<span class="mail-badge mail-badge-new">Email mới</span>' : '';
    const otpBadge = hasOtp ? '<span class="text-[11px] px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 font-semibold">OTP</span>' : '';
    const linkBadge = hasLinks ? '<span class="text-[11px] px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 font-semibold">Link</span>' : '';
    const sender = escapeHtml(message.from_name || message.from_email || 'Unknown Sender');
    const subject = escapeHtml(message.subject || '(No subject)');
    const aliasAddress = escapeHtml(message.recipient_address);
    const avatar = getAvatarPresentation(message);
    const starAlwaysVisible = message.important || hasOtp ? 'always-visible' : '';
    const starActive = message.important ? 'active' : '';

    return `
      <div class="email-row ${selectedCls} ${unreadCls} ${recentCls} pr-4 pl-10 sm:pr-6 sm:pl-12 py-4 flex items-start gap-3" data-message-id="${message.id}" data-recipient-address="${escapeAttribute(message.recipient_address)}" data-recent-message="${isRecentMessage(message.id) ? 'true' : 'false'}">
        <label class="row-checkbox" aria-label="Chọn email ${message.id}">
          <input class="row-checkbox-input" type="checkbox" data-select-message="${message.id}" ${selectedCls ? 'checked' : ''}>
          <span class="row-checkbox-box">
            <i data-lucide="check" class="w-3.5 h-3.5"></i>
          </span>
        </label>
        <div class="mail-avatar flex-shrink-0 mt-0.5" style="background:${avatar.background}; color:${avatar.color};">
          ${avatar.label}
        </div>
        <div class="flex-1 min-w-0">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <p class="text-sm font-semibold text-gray-900 truncate">${aliasAddress}</p>
              <p class="text-sm ${message.unread ? 'font-semibold text-gray-700' : 'font-medium text-gray-500'} truncate mt-0.5">${sender}</p>
              <p class="text-sm ${message.unread ? 'text-gray-800' : 'text-gray-500'} truncate mt-0.5">${subject}</p>
            </div>
            <div class="flex flex-col items-end gap-2 flex-shrink-0">
              <span class="text-xs text-gray-400 whitespace-nowrap" data-relative-time="${escapeAttribute(message.received_at)}">${formatRelativeDate(message.received_at)}</span>
              <div class="row-actions">
                <button class="row-action-btn row-star-btn ${starAlwaysVisible} ${starActive}" type="button" title="Đánh dấu quan trọng" data-toggle-important="${message.id}">
                  <i data-lucide="star" class="w-4 h-4 pointer-events-none"></i>
                </button>
                <button class="row-action-btn row-delete-btn" type="button" title="Xóa email" data-delete-message="${message.id}">
                  <i data-lucide="trash" class="w-4 h-4 pointer-events-none"></i>
                </button>
              </div>
            </div>
          </div>
          <div class="flex items-center gap-2 mt-3 flex-wrap">
            ${newBadge}
            ${otpBadge}
            ${linkBadge}
          </div>
        </div>
      </div>
    `;
  }).join('');

  dom.emailList.querySelectorAll('[data-message-id]').forEach((row) => {
    row.addEventListener('mousedown', (event) => {
      if (event.shiftKey || event.ctrlKey || event.metaKey) {
        event.preventDefault();
      }
    });
    row.addEventListener('click', async (event) => {
      await handleMessageRowClick(Number(row.dataset.messageId), event, row.dataset.recipientAddress || null);
    });
  });
  dom.emailList.querySelectorAll('[data-delete-message]').forEach((button) => {
    button.addEventListener('click', async (event) => {
      event.stopPropagation();
      await deleteMessage(Number(button.dataset.deleteMessage));
    });
  });
  dom.emailList.querySelectorAll('[data-select-message]').forEach((input) => {
    input.addEventListener('click', async (event) => {
      event.stopPropagation();
      const row = input.closest('[data-message-id]');
      await toggleMessageSelection(
        Number(input.dataset.selectMessage),
        row?.dataset.recipientAddress || null,
      );
    });
  });
  dom.emailList.querySelectorAll('[data-toggle-important]').forEach((button) => {
    button.addEventListener('click', async (event) => {
      event.stopPropagation();
      await toggleImportant(Number(button.dataset.toggleImportant));
    });
  });

  lucide.createIcons();
  updateBulkToolbar();
}

function renderSentMessageRow(message) {
  const selectedCls = isMessageSelected(message.id) ? 'selected' : '';
  const recipients = formatAddressList(message.to, 'Không có người nhận');
  const subject = escapeHtml(message.subject || '(No subject)');
  const snippet = escapeHtml(message.snippet || message.text_body || '');
  const avatar = getAvatarPresentation(message);
  const attachmentCount = Number(message.attachment_count || (Array.isArray(message.attachments) ? message.attachments.length : 0));
  const modeLabel = getSentModeLabel(message.mode);
  const attachmentBadge = attachmentCount
    ? `<span class="mail-badge mail-badge-neutral"><i data-lucide="paperclip" class="w-3 h-3"></i>${attachmentCount} tệp</span>`
    : '';

  return `
    <div class="email-row ${selectedCls} pr-4 pl-10 sm:pr-6 sm:pl-12 py-4 flex items-start gap-3" data-message-id="${message.id}" data-recent-message="false">
      <label class="row-checkbox" aria-label="Chọn email đã gửi ${message.id}">
        <input class="row-checkbox-input" type="checkbox" data-select-message="${message.id}" ${selectedCls ? 'checked' : ''}>
        <span class="row-checkbox-box">
          <i data-lucide="check" class="w-3.5 h-3.5"></i>
        </span>
      </label>
      <div class="mail-avatar flex-shrink-0 mt-0.5" style="background:${avatar.background}; color:${avatar.color};">
        ${avatar.label}
      </div>
      <div class="flex-1 min-w-0">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <p class="text-sm font-semibold text-gray-900 truncate">Đến: ${escapeHtml(recipients)}</p>
            <p class="text-sm font-medium text-gray-500 truncate mt-0.5">Từ ${escapeHtml(message.from_email || 'DarkAmbient')}</p>
            <p class="text-sm text-gray-600 truncate mt-0.5">${subject}</p>
            ${snippet ? `<p class="text-sm text-gray-400 truncate mt-0.5">${snippet}</p>` : ''}
          </div>
          <div class="flex flex-col items-end gap-2 flex-shrink-0">
            <span class="text-xs text-gray-400 whitespace-nowrap" data-relative-time="${escapeAttribute(message.sent_at || message.received_at)}">${formatRelativeDate(message.sent_at || message.received_at)}</span>
            <div class="row-actions">
              <button class="row-action-btn row-delete-btn" type="button" title="Xóa email đã gửi" data-delete-message="${message.id}">
                <i data-lucide="trash" class="w-4 h-4 pointer-events-none"></i>
              </button>
            </div>
          </div>
        </div>
        <div class="flex items-center gap-2 mt-3 flex-wrap">
          <span class="mail-badge mail-badge-sent"><i data-lucide="send-horizontal" class="w-3 h-3"></i>${modeLabel}</span>
          ${attachmentBadge}
        </div>
      </div>
    </div>
  `;
}

async function loadUsers() {
  const payload = await api('/api/users');
  state.users = payload.items || [];
  renderUsers();
}

function renderUsers() {
  dom.userCount.textContent = `${state.users.length} user`;
  if (!state.users.length) {
    dom.userList.innerHTML = '';
    dom.userEmptyState.classList.remove('hidden');
    lucide.createIcons();
    return;
  }

  dom.userEmptyState.classList.add('hidden');
  dom.userList.innerHTML = state.users.map((user) => {
    const isCurrentUser = state.session?.username === user.username;
    const initials = buildUserInitials(user.username);
    const roleLabel = user.role === 'admin' ? 'ADMIN' : 'USER';
    const lastLogin = user.last_login_at ? formatFullDate(user.last_login_at) : 'Chưa đăng nhập';
    const createdAt = user.created_at ? formatFullDate(user.created_at) : '-';
    const deleteDisabled = isCurrentUser ? 'disabled' : '';
    const deleteTitle = isCurrentUser ? 'Không thể xóa tài khoản đang đăng nhập' : 'Xóa user';

    return `
      <div class="user-row" data-user-id="${user.id}">
        <div class="user-avatar">${escapeHtml(initials)}</div>
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2 flex-wrap">
            <p class="text-sm font-bold text-gray-900">${escapeHtml(user.username)}</p>
            <span class="user-role-badge ${user.role === 'admin' ? 'admin' : ''}">${roleLabel}</span>
            ${isCurrentUser ? '<span class="text-xs font-semibold text-lush-600">đang đăng nhập</span>' : ''}
          </div>
          <p class="text-sm text-gray-500 mt-1">@${escapeHtml(user.username)}</p>
          <p class="text-xs text-gray-400 mt-1">Tạo: ${escapeHtml(createdAt)} · Login gần nhất: ${escapeHtml(lastLogin)}</p>
        </div>
        <div class="flex items-center gap-1 flex-shrink-0">
          <button class="user-action-btn" type="button" title="Sửa user" data-edit-user="${user.id}">
            <i data-lucide="pencil" class="w-4 h-4 pointer-events-none"></i>
          </button>
          <button class="user-action-btn danger" type="button" title="${escapeAttribute(deleteTitle)}" data-delete-user="${user.id}" ${deleteDisabled}>
            <i data-lucide="trash-2" class="w-4 h-4 pointer-events-none"></i>
          </button>
        </div>
      </div>
    `;
  }).join('');

  dom.userList.querySelectorAll('[data-edit-user]').forEach((button) => {
    button.addEventListener('click', () => openEditUserModal(Number(button.dataset.editUser)));
  });
  dom.userList.querySelectorAll('[data-delete-user]').forEach((button) => {
    button.addEventListener('click', () => deleteUser(Number(button.dataset.deleteUser)).catch(handleError));
  });
  lucide.createIcons();
}

function buildUserInitials(username) {
  const cleaned = String(username || '').trim();
  if (!cleaned) {
    return '?';
  }
  return cleaned.slice(0, 2).toUpperCase();
}

function openCreateUserModal() {
  state.editingUserId = null;
  dom.userModalTitle.textContent = 'Tạo user';
  dom.userUsernameInput.value = '';
  dom.userPasswordInput.value = '';
  dom.userPasswordInput.required = true;
  dom.userPasswordHint.classList.add('hidden');
  dom.userRoleInput.value = 'user';
  dom.userFormError.classList.add('hidden');
  dom.saveUserBtn.textContent = 'Tạo user';
  openUserModal();
}

function openEditUserModal(userId) {
  const user = state.users.find((item) => item.id === userId);
  if (!user) {
    return;
  }
  state.editingUserId = userId;
  dom.userModalTitle.textContent = 'Sửa user';
  dom.userUsernameInput.value = user.username || '';
  dom.userPasswordInput.value = '';
  dom.userPasswordInput.required = false;
  dom.userPasswordHint.classList.remove('hidden');
  dom.userRoleInput.value = user.role || 'user';
  dom.userFormError.classList.add('hidden');
  dom.saveUserBtn.textContent = 'Lưu';
  openUserModal();
}

function openUserModal() {
  dom.userModal.classList.remove('hidden');
  dom.userModal.classList.add('flex');
  window.setTimeout(() => dom.userUsernameInput.focus(), 30);
  lucide.createIcons();
}

function closeUserModal() {
  dom.userModal.classList.add('hidden');
  dom.userModal.classList.remove('flex');
  state.editingUserId = null;
}

async function onUserFormSubmit(event) {
  event.preventDefault();
  dom.userFormError.classList.add('hidden');
  dom.saveUserBtn.disabled = true;
  const editingUserId = state.editingUserId;
  const isEditing = Boolean(editingUserId);

  const payload = {
    username: dom.userUsernameInput.value.trim(),
    role: dom.userRoleInput.value,
  };
  const password = dom.userPasswordInput.value;
  if (!isEditing || password) {
    payload.password = password;
  }

  try {
    const url = isEditing ? `/api/users/${editingUserId}` : '/api/users';
    const method = isEditing ? 'PATCH' : 'POST';
    const response = await api(url, { method, body: JSON.stringify(payload) });
    if (isEditing && state.session?.username) {
      const previousUser = state.users.find((item) => item.id === editingUserId);
      if (previousUser?.username === state.session.username) {
        state.session = { username: response.item.username, role: response.item.role };
      }
    }
    closeUserModal();
    await loadUsers();
    showToast(isEditing ? 'Đã cập nhật user' : 'Đã tạo user');
  } catch (error) {
    dom.userFormError.textContent = error.message || 'Không lưu được user';
    dom.userFormError.classList.remove('hidden');
  } finally {
    dom.saveUserBtn.disabled = false;
  }
}

async function deleteUser(userId) {
  const user = state.users.find((item) => item.id === userId);
  if (!user) {
    return;
  }
  if (!window.confirm(`Xóa user ${user.username}?`)) {
    return;
  }
  await api(`/api/users/${userId}`, { method: 'DELETE' });
  await loadUsers();
  showToast('Đã xóa user');
}

async function loadExcludedAliases() {
  const payload = await api('/api/excluded-aliases');
  state.excludedAliases = payload.items || [];
  renderExcludedAliases();
}

function renderExcludedAliases() {
  dom.autoDeleteCount.textContent = `${state.excludedAliases.length} alias`;
  if (!state.excludedAliases.length) {
    dom.autoDeleteList.innerHTML = '';
    dom.autoDeleteEmptyState.classList.remove('hidden');
    lucide.createIcons();
    return;
  }

  dom.autoDeleteEmptyState.classList.add('hidden');
  dom.autoDeleteList.innerHTML = state.excludedAliases.map((item) => {
    const createdAt = item.created_at ? formatFullDate(item.created_at) : '-';
    const reason = item.reason ? escapeHtml(item.reason) : 'Không có ghi chú';
    return `
      <div class="auto-delete-row" data-excluded-alias-id="${item.id}">
        <div class="auto-delete-row-icon">
          <i data-lucide="mail-x" class="w-4 h-4"></i>
        </div>
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2 flex-wrap">
            <p class="text-sm font-bold text-gray-900 break-all">${escapeHtml(item.address)}</p>
            <span class="auto-delete-badge">Tự động xoá</span>
          </div>
          <p class="text-sm text-gray-500 mt-1">${reason}</p>
          <p class="text-xs text-gray-400 mt-1">Thêm lúc: ${escapeHtml(createdAt)}</p>
        </div>
        <button class="user-action-btn danger" type="button" title="Bỏ loại trừ" data-delete-excluded-alias="${item.id}">
          <i data-lucide="trash-2" class="w-4 h-4 pointer-events-none"></i>
        </button>
      </div>
    `;
  }).join('');

  dom.autoDeleteList.querySelectorAll('[data-delete-excluded-alias]').forEach((button) => {
    button.addEventListener('click', () => deleteExcludedAlias(Number(button.dataset.deleteExcludedAlias)).catch(handleError));
  });
  lucide.createIcons();
}

async function onAutoDeleteFormSubmit(event) {
  event.preventDefault();
  const address = dom.autoDeleteAddressInput.value.trim();
  const reason = dom.autoDeleteReasonInput.value.trim();
  if (!address) {
    showToast('Nhập alias cần loại trừ');
    return;
  }

  dom.saveAutoDeleteBtn.disabled = true;
  try {
    await api('/api/excluded-aliases', {
      method: 'POST',
      body: JSON.stringify({ address, reason }),
    });
    dom.autoDeleteAddressInput.value = '';
    dom.autoDeleteReasonInput.value = '';
    await Promise.all([
      loadExcludedAliases(),
      loadMessages({ preserveDetail: true }),
    ]);
    showToast('Đã thêm alias tự động xoá');
  } finally {
    dom.saveAutoDeleteBtn.disabled = false;
  }
}

async function deleteExcludedAlias(excludedAliasId) {
  const item = state.excludedAliases.find((alias) => alias.id === excludedAliasId);
  if (!item) {
    return;
  }
  if (!window.confirm(`Bỏ loại trừ ${item.address}?`)) {
    return;
  }
  await api(`/api/excluded-aliases/${excludedAliasId}`, { method: 'DELETE' });
  await loadExcludedAliases();
  showToast('Đã bỏ alias khỏi danh sách tự động xoá');
}


async function loadForwardingRules() {
  const query = new URLSearchParams();
  if (state.forwardingSearch.trim()) {
    query.set('search', state.forwardingSearch.trim());
  }
  const payload = await api(`/api/forwarding-rules${query.toString() ? `?${query.toString()}` : ''}`);
  state.forwardingRules = payload.items || [];
  renderForwardingRules();
}

function onForwardingSearchChange(event) {
  state.forwardingSearch = event.target.value;
  clearTimeout(mainSearchTimer);
  mainSearchTimer = window.setTimeout(() => {
    loadForwardingRules().catch(handleError);
  }, 180);
}

function renderForwardingRules() {
  dom.forwardingCount.textContent = `${state.forwardingRules.length} quy tắc`;
  if (!state.forwardingRules.length) {
    dom.forwardingList.innerHTML = '';
    dom.forwardingEmptyState.classList.remove('hidden');
    lucide.createIcons();
    return;
  }

  dom.forwardingEmptyState.classList.add('hidden');
  dom.forwardingList.innerHTML = state.forwardingRules.map((rule) => {
    const statusLabel = rule.enabled ? 'Đang bật' : 'Đã tạm dừng';
    const statusClass = rule.enabled ? 'forwarding-badge-active' : 'forwarding-badge-paused';
    const lastForwarded = rule.last_forwarded_at
      ? `Chuyển tiếp gần nhất: ${escapeHtml(formatFullDate(rule.last_forwarded_at))}`
      : 'Chưa có thư mới được chuyển tiếp';
    const errorLine = rule.last_status === 'retrying' && rule.last_error
      ? `<p class="forwarding-error mt-1">Lần gửi gần nhất lỗi, hệ thống đang tự thử lại.</p>`
      : '';
    return `
      <div class="auto-delete-row" data-forwarding-rule-id="${rule.id}">
        <div class="auto-delete-row-icon">
          <i data-lucide="forward" class="w-4 h-4"></i>
        </div>
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2 flex-wrap">
            <p class="text-sm font-bold text-gray-900 break-all">${escapeHtml((rule.source_addresses || [rule.source_address]).join(', '))}</p>
            <i data-lucide="arrow-right" class="w-4 h-4 text-gray-400 flex-shrink-0"></i>
            <p class="text-sm font-semibold text-gray-700 break-all">${escapeHtml((rule.target_addresses || [rule.target_address]).join(', '))}</p>
            <span class="forwarding-badge ${statusClass}">${statusLabel}</span>
          </div>
          <p class="text-xs text-gray-400 mt-1">${lastForwarded}</p>
          ${errorLine}
        </div>
        <div class="flex items-center gap-1">
          <button class="user-action-btn" type="button" title="Sửa quy tắc" data-edit-forwarding-rule="${rule.id}">
            <i data-lucide="pencil" class="w-4 h-4 pointer-events-none"></i>
          </button>
          <button class="user-action-btn" type="button" title="${rule.enabled ? 'Tạm dừng' : 'Bật chuyển tiếp'}" data-toggle-forwarding-rule="${rule.id}">
            <i data-lucide="${rule.enabled ? 'pause' : 'play'}" class="w-4 h-4 pointer-events-none"></i>
          </button>
          <button class="user-action-btn danger" type="button" title="Xóa quy tắc" data-delete-forwarding-rule="${rule.id}">
            <i data-lucide="trash-2" class="w-4 h-4 pointer-events-none"></i>
          </button>
        </div>
      </div>
    `;
  }).join('');

  dom.forwardingList.querySelectorAll('[data-toggle-forwarding-rule]').forEach((button) => {
    button.addEventListener('click', () => toggleForwardingRule(Number(button.dataset.toggleForwardingRule)).catch(handleError));
  });
  dom.forwardingList.querySelectorAll('[data-edit-forwarding-rule]').forEach((button) => {
    button.addEventListener('click', () => openForwardingEditModal(Number(button.dataset.editForwardingRule)));
  });
  dom.forwardingList.querySelectorAll('[data-delete-forwarding-rule]').forEach((button) => {
    button.addEventListener('click', () => deleteForwardingRule(Number(button.dataset.deleteForwardingRule)).catch(handleError));
  });
  lucide.createIcons();
}

async function onForwardingFormSubmit(event) {
  event.preventDefault();
  const sourceAddress = dom.forwardingSourceInput.value.trim();
  const targetAddress = dom.forwardingTargetInput.value.trim();
  if (!sourceAddress || !targetAddress) {
    showToast('Nhập đủ alias và email nhận chuyển tiếp');
    return;
  }

  dom.saveForwardingBtn.disabled = true;
  try {
    await api('/api/forwarding-rules', {
      method: 'POST',
      body: JSON.stringify({ source_addresses: sourceAddress, target_addresses: targetAddress }),
    });
    dom.forwardingSourceInput.value = '';
    dom.forwardingTargetInput.value = '';
    await loadForwardingRules();
    showToast('Đã bật tự động chuyển tiếp');
  } catch (error) {
    handleError(error);
  } finally {
    dom.saveForwardingBtn.disabled = false;
  }
}

function openForwardingEditModal(ruleId) {
  const rule = state.forwardingRules.find((item) => item.id === ruleId);
  if (!rule) {
    return;
  }
  state.editingForwardingRuleId = ruleId;
  dom.forwardingEditSourceInput.value = (rule.source_addresses || [rule.source_address]).join(', ');
  dom.forwardingEditTargetInput.value = (rule.target_addresses || [rule.target_address]).join(', ');
  dom.forwardingEditError.classList.add('hidden');
  dom.forwardingEditError.textContent = '';
  dom.forwardingEditModal.classList.remove('hidden');
  dom.forwardingEditModal.classList.add('flex');
  window.setTimeout(() => dom.forwardingEditSourceInput.focus(), 30);
  lucide.createIcons();
}

function closeForwardingEditModal() {
  dom.forwardingEditModal.classList.add('hidden');
  dom.forwardingEditModal.classList.remove('flex');
  dom.forwardingEditError.classList.add('hidden');
  dom.forwardingEditError.textContent = '';
  state.editingForwardingRuleId = null;
}

async function onForwardingEditSubmit(event) {
  event.preventDefault();
  const ruleId = state.editingForwardingRuleId;
  if (!ruleId) {
    return;
  }
  dom.forwardingEditError.classList.add('hidden');
  dom.saveForwardingEditBtn.disabled = true;
  try {
    await api(`/api/forwarding-rules/${ruleId}`, {
      method: 'PATCH',
      body: JSON.stringify({
        source_addresses: dom.forwardingEditSourceInput.value.trim(),
        target_addresses: dom.forwardingEditTargetInput.value.trim(),
      }),
    });
    closeForwardingEditModal();
    await loadForwardingRules();
    showToast('Đã cập nhật quy tắc chuyển tiếp');
  } catch (error) {
    dom.forwardingEditError.textContent = error.message || 'Không cập nhật được quy tắc';
    dom.forwardingEditError.classList.remove('hidden');
  } finally {
    dom.saveForwardingEditBtn.disabled = false;
  }
}

async function toggleForwardingRule(ruleId) {
  const rule = state.forwardingRules.find((item) => item.id === ruleId);
  if (!rule) {
    return;
  }
  await api(`/api/forwarding-rules/${ruleId}`, {
    method: 'PATCH',
    body: JSON.stringify({ enabled: !rule.enabled }),
  });
  await loadForwardingRules();
  showToast(rule.enabled ? 'Đã tạm dừng chuyển tiếp' : 'Đã bật chuyển tiếp');
}

async function deleteForwardingRule(ruleId) {
  const rule = state.forwardingRules.find((item) => item.id === ruleId);
  if (!rule || !window.confirm(`Xóa chuyển tiếp ${rule.source_address} tới ${rule.target_address}?`)) {
    return;
  }
  await api(`/api/forwarding-rules/${ruleId}`, { method: 'DELETE' });
  await loadForwardingRules();
  showToast('Đã xóa quy tắc chuyển tiếp');
}

async function handleMessageRowClick(messageId, event, recipientAddress = null) {
  if (event.shiftKey) {
    const rangeIds = getRangeSelectionIds(messageId);
    if (rangeIds.length > 1) {
      const anchorId = state.selectionAnchorMessageId && getVisibleMessageIds().includes(state.selectionAnchorMessageId)
        ? state.selectionAnchorMessageId
        : messageId;
      await openMessage(messageId, { selectionIds: rangeIds, anchorId, recipientAddress });
      return;
    }
  }

  if (event.ctrlKey || event.metaKey) {
    await toggleMessageSelection(messageId, recipientAddress);
    return;
  }

  await openMessage(messageId, { recipientAddress });
}

async function openMessage(messageId, options = {}) {
  const {
    selectionIds = [messageId],
    anchorId = messageId,
    recipientAddress = null,
  } = options;
  try {
    const rowMessage = state.messages.find((item) => (
      item.id === messageId
      && (!recipientAddress || item.recipient_address === recipientAddress)
    ));
    const isSent = isSentMessage(rowMessage) || isSentFolder();
    const endpointBase = isSent
      ? `/api/sent-messages/${messageId}`
      : `/api/messages/${messageId}`;
    const endpoint = !isSent && rowMessage?.recipient_address
      ? `${endpointBase}?recipient_address=${encodeURIComponent(rowMessage.recipient_address)}`
      : endpointBase;
    const payload = await api(endpoint);
    state.selectedMessageId = messageId;
    state.selectedRecipientAddress = isSent ? null : payload.item.recipient_address;
    state.selectedMessageIds = normalizeSelectedMessageIds(selectionIds);
    state.selectionAnchorMessageId = anchorId;
    state.selectedMessageCache = payload.item;
    state.composeDraft = null;
    delete state.recentMessageIds[messageId];
    renderMessages();
    renderDetail(payload.item);
    if (window.innerWidth < 1024) {
      dom.mobileDetail.classList.remove('hidden');
    }
  } catch (error) {
    handleError(error);
  }
}

async function deleteMessage(messageId) {
  const targetIds = getDeleteTargetIds(messageId);
  await deleteMessages(targetIds);
}

async function deleteMessages(messageIds) {
  const uniqueIds = Array.from(new Set(messageIds.map(Number).filter(Boolean)));
  if (!uniqueIds.length) {
    return;
  }

  const confirmed = window.confirm(
    uniqueIds.length === 1
      ? 'Xóa email này khỏi dashboard?'
      : `Xóa ${uniqueIds.length} email đã chọn khỏi dashboard?`,
  );
  if (!confirmed) {
    return;
  }

  try {
    const endpointPrefix = isSentFolder() ? '/api/sent-messages' : '/api/messages';
    await Promise.all(uniqueIds.map((messageId) => api(`${endpointPrefix}/${messageId}`, { method: 'DELETE' })));
    uniqueIds.forEach((messageId) => {
      delete state.recentMessageIds[messageId];
      delete state.messageTranslations[messageId];
      delete state.messageTranslationVisibility[messageId];
    });
    state.selectedMessageIds = state.selectedMessageIds.filter((messageId) => !uniqueIds.includes(messageId));
    if (!state.selectedMessageIds.length) {
      state.selectionAnchorMessageId = null;
    }
    if (uniqueIds.includes(state.selectedMessageId)) {
      state.selectedMessageId = null;
      state.selectedRecipientAddress = null;
      state.selectedMessageCache = null;
      state.composeDraft = null;
      resetDetail();
    }
    await loadMessages({ preserveDetail: true });
    showToast(uniqueIds.length === 1 ? 'Đã xóa email' : `Đã xóa ${uniqueIds.length} email`);
  } catch (error) {
    handleError(error);
  }
}

async function toggleMessageSelection(messageId, recipientAddress = null) {
  const currentSelection = new Set(getVisibleSelectedMessageIds());
  const willSelect = !currentSelection.has(messageId);

  if (willSelect) {
    currentSelection.add(messageId);
  } else {
    currentSelection.delete(messageId);
  }

  const nextIds = getVisibleMessageIds().filter((id) => currentSelection.has(id));
  state.selectionAnchorMessageId = messageId;

  if (!nextIds.length) {
    clearSelection();
    return;
  }

  const activeId = willSelect
    ? messageId
    : (nextIds.includes(state.selectedMessageId) ? state.selectedMessageId : nextIds[nextIds.length - 1]);

  if (state.selectedMessageId === activeId && state.selectedMessageCache) {
    state.selectedMessageIds = nextIds;
    renderMessages();
    return;
  }

  const activeRecipientAddress = activeId === messageId
    ? recipientAddress
    : state.selectedRecipientAddress;
  await openMessage(activeId, {
    selectionIds: nextIds,
    anchorId: messageId,
    recipientAddress: activeRecipientAddress,
  });
}

async function selectAllVisibleMessages() {
  const nextIds = getVisibleMessageIds();
  if (!nextIds.length) {
    return;
  }

  const anchorId = state.selectionAnchorMessageId && nextIds.includes(state.selectionAnchorMessageId)
    ? state.selectionAnchorMessageId
    : nextIds[0];
  const activeId = nextIds.includes(state.selectedMessageId) ? state.selectedMessageId : nextIds[0];

  if (state.selectedMessageId === activeId && state.selectedMessageCache) {
    state.selectedMessageIds = nextIds;
    state.selectionAnchorMessageId = anchorId;
    renderMessages();
  } else {
    await openMessage(activeId, { selectionIds: nextIds, anchorId });
  }

  showToast(`Đã chọn ${nextIds.length} email`);
}

async function toggleSelectVisibleMessages() {
  const visibleIds = getVisibleMessageIds();
  if (!visibleIds.length) {
    return;
  }

  if (getVisibleSelectedMessageIds().length === visibleIds.length) {
    clearSelection();
    showToast('\u0110\u00e3 b\u1ecf ch\u1ecdn trang n\u00e0y');
    return;
  }

  await selectAllVisibleMessages();
}

async function deleteSelectedMessages() {
  const targetIds = getVisibleSelectedMessageIds();
  if (!targetIds.length) {
    showToast('Ch\u01b0a ch\u1ecdn email \u0111\u1ec3 x\u00f3a');
    return;
  }
  await deleteMessages(targetIds);
}

async function deleteAllMessagesInScope() {
  if (!state.messages.length) {
    showToast('Kh\u00f4ng c\u00f3 email \u0111\u1ec3 x\u00f3a');
    return;
  }

  const confirmed = window.confirm(
    `${getDeleteAllScopeLabel()}\nH\u00e0nh \u0111\u1ed9ng n\u00e0y s\u1ebd x\u00f3a to\u00e0n b\u1ed9 email kh\u1edbp b\u1ed9 l\u1ecdc hi\u1ec7n t\u1ea1i, kh\u00f4ng ph\u1ee5 thu\u1ed9c page \u0111ang xem.`,
  );
  if (!confirmed) {
    return;
  }

  const params = getMessageQueryParams();
  const endpoint = isSentFolder() ? '/api/sent-messages' : '/api/messages';
  const payload = await api(`${endpoint}?${params.toString()}`, { method: 'DELETE' });
  state.selectedMessageId = null;
  state.selectedRecipientAddress = null;
  state.selectedMessageIds = [];
  state.selectionAnchorMessageId = null;
  state.selectedMessageCache = null;
  state.composeDraft = null;
  state.messageTranslations = {};
  state.messageTranslationVisibility = {};
  state.currentPage = 1;
  resetDetail();
  await loadMessages({ preserveDetail: true });
  showToast(payload.deleted_count ? `\u0110\u00e3 x\u00f3a ${payload.deleted_count} email` : 'Kh\u00f4ng c\u00f3 email \u0111\u1ec3 x\u00f3a');
}

function getDeleteAllScopeLabel() {
  if (state.mainSearch.trim()) {
    return `X\u00f3a t\u1ea5t c\u1ea3 email kh\u00f3a "${state.mainSearch.trim()}"?`;
  }

  const labels = {
    all: 'X\u00f3a to\u00e0n b\u1ed9 email trong h\u1ed9p th\u01b0?',
    unread: 'X\u00f3a to\u00e0n b\u1ed9 email ch\u01b0a \u0111\u1ecdc?',
    important: 'X\u00f3a to\u00e0n b\u1ed9 email quan tr\u1ecdng?',
    sent: 'X\u00f3a to\u00e0n b\u1ed9 email \u0111\u00e3 g\u1eedi?',
  };
  return labels[state.currentFilter] || 'X\u00f3a to\u00e0n b\u1ed9 email trong inbox hi\u1ec7n t\u1ea1i?';
}

function mergeMessageFlags(existing, updated) {
  return {
    ...existing,
    important: Boolean(updated.important),
    unread: updated.unread ?? existing.unread,
  };
}

async function toggleImportant(messageId) {
  const message = state.messages.find((item) => item.id === messageId) || state.selectedMessageCache;
  if (!message) {
    return;
  }

  try {
    const payload = await api(`/api/messages/${messageId}/important`, {
      method: 'PATCH',
      body: JSON.stringify({ important: !message.important }),
    });
    const updated = payload.item;
    state.messages = state.messages.map((item) => (
      item.id === messageId ? mergeMessageFlags(item, updated) : item
    ));
    if (state.selectedMessageId === messageId) {
      state.selectedMessageCache = mergeMessageFlags(
        state.selectedMessageCache || updated,
        updated,
      );
      renderDetail(state.selectedMessageCache);
    }
    if (state.currentFilter === 'important' && !updated.important) {
      await loadMessages({ preserveDetail: true });
    } else {
      state.messageListSignature = buildMessageListSignature(state.messages);
      renderMessages();
      updateHeader();
      renderPagination();
    }
    showToast(updated.important ? 'Đã lưu vào Quan trọng' : 'Đã bỏ khỏi Quan trọng');
  } catch (error) {
    handleError(error);
  }
}

function renderDetail(message) {
  if (isSentMessage(message)) {
    renderSentDetail(message);
    return;
  }

  const avatar = getAvatarPresentation(message);
  const composePanel = renderComposePanel(message);
  const originalSubject = message.subject || '(No subject)';
  const originalBody = message.text_body || message.snippet || '';
  const translation = state.messageTranslations[message.id];
  const hasTranslation = hasUsableTranslation(translation);
  const isTranslationVisible = Boolean(state.messageTranslationVisibility[message.id] && hasTranslation);
  const canToggleTranslation = shouldRenderTranslateButton(message, translation);
  const detailSubject = isTranslationVisible ? (translation.translated_subject || originalSubject) : originalSubject;
  const detailBody = isTranslationVisible ? (translation.translated_body || originalBody) : originalBody;
  const detailBodySection = renderDetailBodySection(message, detailBody, {
    isTranslationVisible,
    translatedHtml: isTranslationVisible ? (translation?.translated_html || '') : '',
  });
  const attachmentSection = renderAttachmentSection(message);
  const translationMeta = renderTranslationMeta(message.id, translation, isTranslationVisible);
  const detailHTML = `
    <div class="detail-fade-in detail-pane-shell">
      <div class="detail-scroll-area" data-detail-scroll>
        <div class="detail-reader">
          ${composePanel}

          <section class="detail-flat-section detail-flat-hero">
            <div class="flex items-start gap-4">
              <div class="mail-avatar-detail flex-shrink-0" style="background:${avatar.background}; color:${avatar.color};">
                ${avatar.label}
              </div>
              <div class="flex-1 min-w-0">
                <p class="detail-kicker">Alias nhận mail</p>
                <h4 class="font-fustat text-xl font-bold text-gray-900 break-all">${escapeHtml(message.recipient_address)}</h4>
                <div class="detail-meta-stack mt-3">
                  <p class="text-sm text-gray-700">${escapeHtml(message.from_name || 'Unknown Sender')}</p>
                  <p class="text-sm text-gray-400 break-all">${escapeHtml(message.from_email || '')}</p>
                </div>
              </div>
            </div>

            <div class="detail-title-block">
              <p class="detail-kicker">Tiêu đề</p>
              <h3 class="font-fustat text-[30px] font-bold text-gray-900 leading-snug">${escapeHtml(detailSubject)}</h3>
              ${translationMeta}
            </div>

            <div class="detail-meta-row">
              <div class="detail-meta-main">
                <i data-lucide="calendar" class="w-4 h-4 text-gray-400"></i>
                <span class="text-sm text-gray-500">${formatFullDate(message.received_at)}</span>
              </div>
              ${canToggleTranslation ? `
                <button
                  type="button"
                  class="detail-translate-btn ${translation?.loading ? 'loading' : ''} ${isTranslationVisible ? 'active' : ''}"
                  data-translate-message="${message.id}"
                  title="${isTranslationVisible ? 'Xem bản gốc' : 'Dịch sang tiếng Việt'}"
                  aria-label="${isTranslationVisible ? 'Xem bản gốc' : 'Dịch sang tiếng Việt'}"
                >
                  <i data-lucide="${translation?.loading ? 'loader-circle' : 'languages'}" class="w-4 h-4"></i>
                </button>
              ` : ''}
            </div>

            ${renderDetailExtras(message)}
          </section>

          <section class="detail-flat-section">
            <div class="detail-section-heading">
              <p class="detail-kicker">Nội dung email</p>
            </div>
            ${detailBodySection}
          </section>

          ${attachmentSection}
        </div>
      </div>

      <div class="detail-sticky-footer">
        ${renderDetailActionBar(message)}
      </div>
    </div>
  `;

  dom.detailContent.innerHTML = detailHTML;
  dom.mobileDetailContent.innerHTML = detailHTML;
  lucide.createIcons();
  syncEmailFrameHeights();

  bindDetailActions();
}

function renderSentDetail(message) {
  const avatar = getAvatarPresentation(message);
  const recipients = formatAddressList(message.to, 'Không có người nhận');
  const ccRecipients = formatAddressList(message.cc, '');
  const sentAt = message.sent_at || message.received_at;
  const attachmentSection = renderAttachmentSection(message);
  const detailHTML = `
    <div class="detail-fade-in detail-pane-shell">
      <div class="detail-scroll-area" data-detail-scroll>
        <div class="detail-reader">
          <section class="detail-flat-section detail-flat-hero">
            <div class="flex items-start gap-4">
              <div class="mail-avatar-detail flex-shrink-0" style="background:${avatar.background}; color:${avatar.color};">
                ${avatar.label}
              </div>
              <div class="flex-1 min-w-0">
                <p class="detail-kicker">Đã gửi tới</p>
                <h4 class="font-fustat text-xl font-bold text-gray-900 break-all">${escapeHtml(recipients)}</h4>
                <div class="detail-meta-stack mt-3">
                  <p class="text-sm text-gray-700">Từ ${escapeHtml(message.from_email || 'DarkAmbient')}</p>
                  ${ccRecipients ? `<p class="text-sm text-gray-400 break-all">CC ${escapeHtml(ccRecipients)}</p>` : ''}
                </div>
              </div>
            </div>

            <div class="detail-title-block">
              <p class="detail-kicker">Tiêu đề</p>
              <h3 class="font-fustat text-[30px] font-bold text-gray-900 leading-snug">${escapeHtml(message.subject || '(No subject)')}</h3>
            </div>

            <div class="detail-meta-row">
              <div class="detail-meta-main">
                <i data-lucide="send-horizontal" class="w-4 h-4 text-gray-400"></i>
                <span class="text-sm text-gray-500">${formatFullDate(sentAt)}</span>
              </div>
              <span class="mail-badge mail-badge-sent">${getSentModeLabel(message.mode)}</span>
            </div>

            <div class="detail-address-grid">
              <div>
                <p class="detail-kicker">Từ</p>
                <p>${escapeHtml(message.from_email || '-')}</p>
              </div>
              <div>
                <p class="detail-kicker">Tới</p>
                <p>${escapeHtml(recipients)}</p>
              </div>
              ${ccRecipients ? `
                <div>
                  <p class="detail-kicker">CC</p>
                  <p>${escapeHtml(ccRecipients)}</p>
                </div>
              ` : ''}
              <div>
                <p class="detail-kicker">Message-ID</p>
                <p>${escapeHtml(message.message_id || '-')}</p>
              </div>
            </div>
          </section>

          <section class="detail-flat-section">
            <div class="detail-section-heading">
              <p class="detail-kicker">Nội dung đã gửi</p>
            </div>
            <div class="detail-body-copy">${linkifyText(message.text_body || 'Email này không có nội dung text.')}</div>
          </section>

          ${attachmentSection}
        </div>
      </div>

      <div class="detail-sticky-footer">
        <section class="detail-flat-toolbar detail-footer-shell">
          <div class="flex flex-wrap items-center gap-3">
            <button type="button" data-copy-text="${escapeAttribute(recipients)}" data-copy-success="Đã copy người nhận" class="detail-footer-action">
              <i data-lucide="copy" class="w-4 h-4"></i>
              Copy người nhận
            </button>
            <button type="button" data-copy-text="${escapeAttribute(message.subject || '')}" data-copy-success="Đã copy tiêu đề" class="detail-footer-action">
              <i data-lucide="copy-check" class="w-4 h-4"></i>
              Copy tiêu đề
            </button>
          </div>
        </section>
      </div>
    </div>
  `;

  dom.detailContent.innerHTML = detailHTML;
  dom.mobileDetailContent.innerHTML = detailHTML;
  lucide.createIcons();
  bindDetailActions();
}

function renderDetailBodySection(message, detailBody, options = {}) {
  const { isTranslationVisible = false, translatedHtml = '' } = options;
  const normalizedHtml = String(message.html_body || '').trim();
  const normalizedTranslatedHtml = String(translatedHtml || '').trim();
  const normalizedText = String(detailBody || '').trim();

  if (isTranslationVisible && normalizedTranslatedHtml) {
    const frameDocument = buildEmailFrameDocument(normalizedTranslatedHtml);
    return `
      <div class="detail-body-render">
        <iframe
          class="detail-html-frame"
          data-email-frame="true"
          sandbox="allow-popups allow-popups-to-escape-sandbox allow-same-origin"
          loading="lazy"
          referrerpolicy="no-referrer"
          srcdoc="${escapeAttribute(frameDocument)}"
        ></iframe>
      </div>
    `;
  }

  if (!isTranslationVisible && normalizedHtml) {
    const frameDocument = buildEmailFrameDocument(normalizedHtml);
    return `
      <div class="detail-body-render">
        <iframe
          class="detail-html-frame"
          data-email-frame="true"
          sandbox="allow-popups allow-popups-to-escape-sandbox allow-same-origin"
          loading="lazy"
          referrerpolicy="no-referrer"
          srcdoc="${escapeAttribute(frameDocument)}"
        ></iframe>
      </div>
    `;
  }

  return `<div class="detail-body-copy">${linkifyText(normalizedText || 'Email này không có nội dung text preview.')}</div>`;
}

function renderComposePanel(message) {
  const draft = state.composeDraft;
  if (!draft || draft.messageId !== message.id) {
    return '';
  }
  const attachmentCount = Array.isArray(message.attachments) ? message.attachments.length : 0;
  const forwardAttachmentNote = draft.mode === 'forward' && attachmentCount
    ? `<p class="detail-compose-note">${attachmentCount} tệp đính kèm sẽ được gửi cùng email chuyển tiếp.</p>`
    : '';
  const selectedAttachments = renderComposeAttachmentItems(draft.attachments || []);
  const selectedCount = (draft.attachments || []).length;

  return `
    <section class="detail-flat-section detail-compose-section">
      <div class="flex items-start justify-between gap-3">
        <div>
          <h5 class="font-fustat text-lg font-bold text-gray-900">${draft.mode === 'reply' ? 'Trả lời email' : 'Chuyển tiếp email'}</h5>
        </div>
        <button type="button" data-compose-close="true" class="detail-inline-close">
          <i data-lucide="x" class="w-4 h-4"></i>
        </button>
      </div>
      <div class="grid gap-3 mt-5">
        <label class="grid gap-1.5">
          <span class="detail-field-label">Từ</span>
          <input data-compose-field="fromAlias" type="email" value="${escapeAttribute(draft.fromAlias)}" class="detail-field-input" />
        </label>
        <label class="grid gap-1.5">
          <span class="detail-field-label">To</span>
          <input data-compose-field="to" value="${escapeAttribute(draft.to)}" class="detail-field-input" />
        </label>
        <label class="grid gap-1.5">
          <span class="detail-field-label">CC</span>
          <input data-compose-field="cc" value="${escapeAttribute(draft.cc)}" placeholder="cc@example.com, other@example.com" class="detail-field-input" />
        </label>
        <label class="grid gap-1.5">
          <span class="detail-field-label">Subject</span>
          <input data-compose-field="subject" value="${escapeAttribute(draft.subject)}" class="detail-field-input" />
        </label>
        <label class="grid gap-1.5">
          <span class="detail-field-label">Message</span>
          <textarea data-compose-field="body" rows="10" class="detail-field-input detail-field-textarea">${escapeHtml(draft.body)}</textarea>
        </label>
        ${selectedAttachments ? `<div class="compose-attachment-list">${selectedAttachments}</div>` : ''}
      </div>
      <div class="detail-compose-footer">
        <div class="flex flex-wrap items-center gap-3 min-w-0">
          <input type="file" multiple class="hidden" data-compose-attachment-input="true">
          <button type="button" data-compose-attachment-button="true" class="compose-attachment-btn">
            <i data-lucide="paperclip" class="w-4 h-4"></i>
            Đính kèm${selectedCount ? ` (${selectedCount})` : ''}
          </button>
          ${forwardAttachmentNote}
        </div>
        <button type="button" data-compose-send="true" class="detail-send-btn ${draft.mode === 'reply' ? 'detail-send-btn-reply' : 'detail-send-btn-forward'}">
          ${draft.mode === 'reply' ? 'Gửi trả lời' : 'Gửi chuyển tiếp'}
        </button>
      </div>
    </section>
  `;
}

function renderDetailActionBar(message) {
  const draft = state.composeDraft;
  const isReplyActive = draft?.messageId === message.id && draft.mode === 'reply';
  const isForwardActive = draft?.messageId === message.id && draft.mode === 'forward';

  return `
    <section class="detail-flat-toolbar detail-footer-shell">
      <div class="flex flex-wrap items-center gap-3">
        <button type="button" data-compose-action="reply" class="detail-footer-action ${isReplyActive ? 'active' : ''}">
          <i data-lucide="reply" class="w-4 h-4"></i>
          Trả lời
        </button>
        <button type="button" data-compose-action="forward" class="detail-footer-action ${isForwardActive ? 'active accent' : ''}">
          <i data-lucide="forward" class="w-4 h-4"></i>
          Chuyển tiếp
        </button>
      </div>
    </section>
  `;
}

function bindDetailActions() {
  document.querySelectorAll('[data-copy-code]').forEach((button) => {
    button.addEventListener('click', () => copyText(button.dataset.copyCode, 'Đã copy OTP'));
  });
  document.querySelectorAll('[data-copy-text]').forEach((button) => {
    button.addEventListener('click', () => copyText(button.dataset.copyText || '', button.dataset.copySuccess || 'Đã copy'));
  });
  document.querySelectorAll('[data-translate-message]').forEach((button) => {
    button.addEventListener('click', async () => {
      await toggleMessageTranslation(Number(button.dataset.translateMessage));
    });
  });
  document.querySelectorAll('[data-compose-action]').forEach((button) => {
    button.addEventListener('click', () => startCompose(button.dataset.composeAction));
  });
  document.querySelectorAll('[data-compose-close]').forEach((button) => {
    button.addEventListener('click', () => {
      state.composeDraft = null;
      if (state.selectedMessageCache) {
        renderDetail(state.selectedMessageCache);
      }
    });
  });
  document.querySelectorAll('[data-compose-field]').forEach((field) => {
    field.addEventListener('input', () => {
      if (!state.composeDraft) {
        return;
      }
      state.composeDraft[field.dataset.composeField] = field.value;
    });
  });
  document.querySelectorAll('[data-compose-send]').forEach((button) => {
    button.addEventListener('click', async () => {
      await sendCompose();
    });
  });
  document.querySelectorAll('[data-compose-attachment-button]').forEach((button) => {
    button.addEventListener('click', () => {
      button.closest('.detail-compose-section')?.querySelector('[data-compose-attachment-input]')?.click();
    });
  });
  document.querySelectorAll('[data-compose-attachment-input]').forEach((input) => {
    input.addEventListener('change', () => {
      if (!state.composeDraft) {
        return;
      }
      try {
        state.composeDraft.attachments = appendAttachmentFiles(
          state.composeDraft.attachments || [],
          Array.from(input.files || []),
          state.composeDraft.originalAttachmentBytes || 0,
          state.composeDraft.originalAttachmentCount || 0,
        );
        if (state.selectedMessageCache) {
          renderDetail(state.selectedMessageCache);
        }
      } catch (error) {
        showToast(error.message || 'Không thể đính kèm tệp');
      }
    });
  });
  document.querySelectorAll('[data-remove-compose-attachment]').forEach((button) => {
    button.addEventListener('click', () => {
      if (!state.composeDraft) {
        return;
      }
      state.composeDraft.attachments.splice(Number(button.dataset.removeComposeAttachment), 1);
      if (state.selectedMessageCache) {
        renderDetail(state.selectedMessageCache);
      }
    });
  });
}

function startCompose(mode) {
  if (!state.selectedMessageCache) {
    return;
  }
  state.composeDraft = buildComposeDraft(state.selectedMessageCache, mode);
  renderDetail(state.selectedMessageCache);
  requestAnimationFrame(() => {
    document.querySelectorAll('[data-detail-scroll]').forEach((node) => {
      node.scrollTo({ top: 0, behavior: 'smooth' });
    });
    const bodyField = document.querySelector('[data-compose-field="body"]');
    bodyField?.focus();
    const bodyLength = bodyField?.value?.length || 0;
    if (bodyField?.setSelectionRange) {
      bodyField.setSelectionRange(0, 0);
    }
    if (bodyField && bodyLength > 0) {
      bodyField.scrollTop = 0;
    }
  });
}

async function sendCompose() {
  const draft = state.composeDraft;
  if (!draft || !draft.messageId) {
    return;
  }

  const sendButton = document.querySelector('[data-compose-send]');
  const originalLabel = sendButton?.textContent;

  try {
    if (sendButton) {
      sendButton.disabled = true;
      sendButton.textContent = 'Đang gửi...';
    }

    const attachments = await serializeAttachmentFiles(draft.attachments || []);
    const payload = {
      mode: draft.mode,
      from_alias: draft.fromAlias,
      to: draft.to,
      cc: draft.cc,
      subject: draft.subject,
      body: draft.body,
      attachments,
    };
    state.composeDraft = null;
    if (state.selectedMessageCache) {
      renderDetail(state.selectedMessageCache);
    }
    showToast('Đang gửi email...');
    await api(`/api/messages/${draft.messageId}/send`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    showToast(draft.mode === 'reply' ? 'Đã gửi trả lời' : 'Đã gửi chuyển tiếp');
  } catch (error) {
    showToast(error.message || 'Gửi email thất bại');
  } finally {
    if (sendButton) {
      sendButton.disabled = false;
      sendButton.textContent = originalLabel;
    }
  }
}

async function loadSenderAliases() {
  const payload = await api('/api/mailboxes?status=visible');
  state.senderAliases = (payload.items || [])
    .map((item) => String(item.address || '').trim())
    .filter(Boolean);
  dom.senderAliasOptions.innerHTML = state.senderAliases
    .map((address) => `<option value="${escapeAttribute(address)}"></option>`)
    .join('');
}

async function openNewMessageComposer() {
  dom.newMessageForm.reset();
  state.newMessageAttachments = [];
  renderNewMessageAttachments();
  dom.newMessageError.classList.add('hidden');
  dom.newMessageError.textContent = '';
  dom.newMessageModal.classList.remove('hidden');
  dom.newMessageModal.classList.add('flex');
  try {
    await loadSenderAliases();
  } catch (error) {
    showToast(error.message || 'Không tải được danh sách alias');
  }
  dom.newMessageFrom.value = state.selectedRecipientAddress
    || state.senderAliases[0]
    || 'contact@temp.darkambient.co';
  requestAnimationFrame(() => dom.newMessageFrom.focus());
  lucide.createIcons();
}

function closeNewMessageComposer() {
  dom.newMessageModal.classList.add('hidden');
  dom.newMessageModal.classList.remove('flex');
  dom.newMessageError.classList.add('hidden');
  dom.newMessageError.textContent = '';
  state.newMessageAttachments = [];
  renderNewMessageAttachments();
}

function onNewMessageAttachmentChange() {
  try {
    state.newMessageAttachments = appendAttachmentFiles(
      state.newMessageAttachments,
      Array.from(dom.newMessageAttachmentInput.files || []),
    );
    renderNewMessageAttachments();
  } catch (error) {
    dom.newMessageError.textContent = error.message || 'Không thể đính kèm tệp';
    dom.newMessageError.classList.remove('hidden');
  } finally {
    dom.newMessageAttachmentInput.value = '';
  }
}

function renderNewMessageAttachments() {
  const files = state.newMessageAttachments;
  dom.newMessageAttachmentCount.textContent = files.length ? `(${files.length})` : '';
  dom.newMessageAttachmentCount.classList.toggle('hidden', !files.length);
  dom.newMessageAttachmentList.classList.toggle('hidden', !files.length);
  dom.newMessageAttachmentList.innerHTML = renderComposeAttachmentItems(files, 'new');
  dom.newMessageAttachmentList.querySelectorAll('[data-remove-new-attachment]').forEach((button) => {
    button.addEventListener('click', () => {
      state.newMessageAttachments.splice(Number(button.dataset.removeNewAttachment), 1);
      renderNewMessageAttachments();
    });
  });
  lucide.createIcons();
}

async function sendNewMessage(event) {
  event.preventDefault();
  dom.newMessageError.classList.add('hidden');
  dom.newMessageError.textContent = '';
  dom.sendNewMessageBtn.disabled = true;

  try {
    const attachments = await serializeAttachmentFiles(state.newMessageAttachments);
    const payload = {
      from_alias: dom.newMessageFrom.value,
      to: dom.newMessageTo.value,
      cc: dom.newMessageCc.value,
      subject: dom.newMessageSubject.value,
      body: dom.newMessageBody.value,
      attachments,
    };
    closeNewMessageComposer();
    showToast('Đang gửi email...');
    await api('/api/messages/send', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    showToast('Đã gửi email');
    if (state.currentFilter === 'sent') {
      loadMessages({ preserveDetail: true }).catch(handleError);
    }
  } catch (error) {
    showToast(error.message || 'Gửi email thất bại');
  } finally {
    dom.sendNewMessageBtn.disabled = false;
  }
}

function getSentModeLabel(mode) {
  if (mode === 'send') {
    return 'Mới';
  }
  if (mode === 'forward') {
    return 'Forward';
  }
  if (mode === 'auto-forward') {
    return 'Tự động';
  }
  return 'Reply';
}

function buildComposeDraft(message, mode) {
  const subjectPrefix = mode === 'reply' ? 'Re:' : 'Fwd:';
  const senderName = message.from_name || message.from_email || 'Unknown Sender';
  const senderEmail = message.from_email || '';
  const quotedBody = message.text_body || message.snippet || '';
  const headerLines = [
    '',
    '---',
    `From: ${senderName}${senderEmail ? ` <${senderEmail}>` : ''}`,
    `To: ${message.recipient_address}`,
    `Subject: ${message.subject || '(No subject)'}`,
    `Date: ${formatFullDate(message.received_at)}`,
    '',
    quotedBody,
  ];

  return {
    messageId: message.id,
    mode,
    fromAlias: message.recipient_address,
    to: mode === 'reply' ? senderEmail : '',
    cc: '',
    subject: `${subjectPrefix} ${message.subject || '(No subject)'}`.trim(),
    body: mode === 'reply'
      ? `\n\n${headerLines.join('\n')}`
      : `Chuyển tiếp email từ ${message.recipient_address}\n${headerLines.join('\n')}`,
    attachments: [],
    originalAttachmentBytes: mode === 'forward'
      ? (message.attachments || []).reduce((total, attachment) => total + Number(attachment.size_bytes || 0), 0)
      : 0,
    originalAttachmentCount: mode === 'forward'
      ? (message.attachments || []).length
      : 0,
  };
}

function appendAttachmentFiles(existingFiles, nextFiles, baseBytes = 0, baseCount = 0) {
  const combined = [...existingFiles, ...nextFiles];
  if (baseCount + combined.length > MAX_ATTACHMENT_COUNT) {
    throw new Error(`Chỉ được đính kèm tối đa ${MAX_ATTACHMENT_COUNT} tệp`);
  }
  const totalBytes = baseBytes + combined.reduce((total, file) => total + Number(file.size || 0), 0);
  if (totalBytes > MAX_ATTACHMENT_TOTAL_BYTES) {
    throw new Error('Tổng dung lượng tệp đính kèm không được vượt quá 18 MB');
  }
  return combined;
}

function renderComposeAttachmentItems(files, scope = 'compose') {
  return files.map((file, index) => `
    <div class="compose-attachment-item">
      <i data-lucide="file" class="w-4 h-4 text-gray-400 flex-shrink-0"></i>
      <div class="min-w-0 flex-1">
        <p class="compose-attachment-name">${escapeHtml(file.name || file.filename || 'Tệp đính kèm')}</p>
        <p class="compose-attachment-size">${formatFileSize(file.size || file.size_bytes || 0)}</p>
      </div>
      <button type="button" class="compose-attachment-remove" title="Bỏ tệp" ${scope === 'new' ? `data-remove-new-attachment="${index}"` : `data-remove-compose-attachment="${index}"`}>
        <i data-lucide="x" class="w-4 h-4 pointer-events-none"></i>
      </button>
    </div>
  `).join('');
}

async function serializeAttachmentFiles(files) {
  return Promise.all(files.map(async (file) => ({
    filename: file.name || 'attachment',
    content_type: file.type || 'application/octet-stream',
    size_bytes: file.size || 0,
    content_base64: arrayBufferToBase64(await file.arrayBuffer()),
  })));
}

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  const chunkSize = 32768;
  for (let offset = 0; offset < bytes.length; offset += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + chunkSize));
  }
  return btoa(binary);
}

function renderTranslationMeta(messageId, translation, isTranslationVisible) {
  if (!translation || translation.loading || translation.skipped) {
    return '';
  }

  const sourceLanguage = formatLanguageLabel(translation.source_language);
  const targetLanguage = formatLanguageLabel(translation.target_language || 'vi');

  return `
    <div class="detail-translation-note">
      <i data-lucide="languages" class="w-3.5 h-3.5"></i>
      <span>${isTranslationVisible ? `Đã dịch ${sourceLanguage} -> ${targetLanguage}` : `Có sẵn bản dịch ${sourceLanguage} -> ${targetLanguage}`}</span>
    </div>
  `;
}

async function toggleMessageTranslation(messageId) {
  const message = state.selectedMessageCache;
  if (!message || message.id !== messageId) {
    return;
  }

  const existing = state.messageTranslations[messageId];
  if (existing?.loading) {
    return;
  }

  if (existing) {
    if (existing.skipped) {
      applyNoTranslateHint(messageId, existing.source_language || 'vi');
      renderDetail(state.selectedMessageCache || message);
      showToast('Email này đã là tiếng Việt');
      return;
    }
    state.messageTranslationVisibility[messageId] = !state.messageTranslationVisibility[messageId];
    renderDetail(message);
    return;
  }

  state.messageTranslations[messageId] = { loading: true };
  renderDetail(message);

  try {
    const payload = await api(`/api/messages/${messageId}/translate`, {
      method: 'POST',
      body: JSON.stringify({ target_language: 'vi' }),
    });
    state.messageTranslations[messageId] = {
      ...payload.item,
      loading: false,
    };
    if (payload.item?.skipped) {
      state.messageTranslationVisibility[messageId] = false;
      applyNoTranslateHint(messageId, payload.item.source_language || 'vi');
      renderDetail(state.selectedMessageCache || message);
      showToast('Email này đã là tiếng Việt');
      return;
    }
    state.messageTranslationVisibility[messageId] = true;
    renderDetail(message);
    showToast('Đã dịch email sang tiếng Việt');
  } catch (error) {
    delete state.messageTranslations[messageId];
    delete state.messageTranslationVisibility[messageId];
    handleError(error);
  }
}

function hasUsableTranslation(translation) {
  return Boolean(
    translation
    && !translation.loading
    && !translation.skipped
    && (translation.translated_subject || translation.translated_body || translation.translated_html),
  );
}

function shouldRenderTranslateButton(message, translation) {
  if (translation?.loading || hasUsableTranslation(translation)) {
    return true;
  }
  return message?.can_translate !== false;
}

function applyNoTranslateHint(messageId, sourceLanguage = 'vi') {
  if (state.selectedMessageCache?.id === messageId) {
    state.selectedMessageCache = {
      ...state.selectedMessageCache,
      can_translate: false,
      language_hint: sourceLanguage,
    };
  }
}

function renderDetailExtras(message) {
  const otpSection = (message.extracted_otps || []).map((item) => `
    <button data-copy-code="${escapeAttribute(item.code)}" class="detail-chip detail-chip-otp hover:opacity-80">
      <i data-lucide="badge-check" class="w-3.5 h-3.5"></i>
      ${escapeHtml(item.code)}
    </button>
  `).join('');

  const linkSection = (message.extracted_links || []).map((item) => `
    <a href="${escapeAttribute(item.url)}" target="_blank" rel="noreferrer" class="detail-chip detail-chip-link hover:opacity-80">
      <i data-lucide="arrow-up-right" class="w-3.5 h-3.5"></i>
      ${escapeHtml(item.type === 'verify' ? 'Mở link verify' : item.type === 'reset_password' ? 'Mở link reset' : 'Mở link')}
    </a>
  `).join('');

  if (!otpSection && !linkSection) {
    return '';
  }

  return `
    <div class="detail-inline-groups">
      ${otpSection ? `<div><p class="detail-kicker mb-3">OTP tìm thấy</p><div class="flex flex-wrap gap-2">${otpSection}</div></div>` : ''}
      ${linkSection ? `<div><p class="detail-kicker mb-3">Link quan trọng</p><div class="flex flex-wrap gap-2">${linkSection}</div></div>` : ''}
    </div>
  `;
}

function renderAttachmentSection(message) {
  const attachments = Array.isArray(message.attachments) ? message.attachments : [];
  if (!attachments.length) {
    return '';
  }

  const items = attachments.map((attachment, index) => {
    const attachmentIndex = Number.isFinite(Number(attachment.index)) ? Number(attachment.index) : index;
    const href = isSentMessage(message)
      ? `/api/sent-messages/${message.id}/attachments/${attachmentIndex}`
      : `/api/messages/${message.id}/attachments/${attachmentIndex}`;
    return `
    <a class="detail-attachment-item" href="${escapeAttribute(href)}" target="_blank" rel="noreferrer" title="Mở tệp đính kèm">
      <div class="detail-attachment-icon">
        <i data-lucide="paperclip" class="w-4 h-4"></i>
      </div>
      <div class="min-w-0 flex-1">
        <p class="detail-attachment-name">${escapeHtml(attachment.filename || 'Unnamed attachment')}</p>
        <p class="detail-attachment-meta">${escapeHtml(attachment.content_type || 'application/octet-stream')} • ${formatFileSize(attachment.size_bytes || 0)}</p>
      </div>
      <span class="detail-attachment-action">
        <i data-lucide="external-link" class="w-3.5 h-3.5"></i>
        Mở
      </span>
    </a>
  `;
  }).join('');

  return `
    <section class="detail-flat-section">
      <div class="detail-section-heading">
        <p class="detail-kicker">Tệp đính kèm</p>
      </div>
      <div class="detail-attachment-list">
        ${items}
      </div>
    </section>
  `;
}

function resetDetail() {
  const html = `
    <div class="h-full flex items-center justify-center px-6 py-12">
      <div class="rounded-[28px] border border-dashed border-gray-200 bg-white px-10 py-14 text-center max-w-md w-full">
        <div class="w-16 h-16 rounded-full bg-gray-50 flex items-center justify-center mb-4 mx-auto">
          <i data-lucide="mouse-pointer-click" class="w-7 h-7 text-gray-300"></i>
        </div>
        <p class="text-sm text-gray-400">Chọn email để xem chi tiết</p>
      </div>
    </div>
  `;
  dom.detailContent.innerHTML = html;
  dom.mobileDetailContent.innerHTML = html;
  lucide.createIcons();
}

function closeMobileDetail() {
  dom.mobileDetail.classList.add('hidden');
}

function updateHeader() {
  const titles = {
    all: 'Tất cả email',
    unread: 'Email chưa đọc',
    important: 'Email quan trọng',
    sent: 'Đã gửi',
  };
  dom.folderTitle.textContent = titles[state.currentFilter] || 'Mail feed';
  dom.folderCount.textContent = `${state.messages.length} email`;
  if (dom.mainSearch) {
    dom.mainSearch.placeholder = isSentFolder()
      ? 'Tìm theo người nhận, subject, nội dung...'
      : 'Tìm theo alias, sender, subject...';
  }
  if (dom.deleteAllBtn) {
    dom.deleteAllBtn.title = isSentFolder()
      ? 'Xóa tất cả email đã gửi đang lọc'
      : 'Xóa tất cả email trong inbox hiện tại';
  }
  if (dom.deleteAllBtn) {
    dom.deleteAllBtn.disabled = !state.messages.length;
  }
}

function updateBulkToolbar() {
  const totalMessages = state.messages.length;
  const visibleCount = getVisibleMessageIds().length;
  const visibleSelectedCount = getVisibleSelectedMessageIds().length;

  if (!dom.selectPageBtn || !dom.deleteSelectedBtn || !dom.selectionSummary) {
    if (dom.deleteAllBtn) {
      dom.deleteAllBtn.disabled = !totalMessages;
    }
    return;
  }

  dom.selectPageBtn.disabled = !visibleCount;
  dom.selectPageBtn.classList.toggle('is-active', Boolean(visibleCount) && visibleSelectedCount === visibleCount);
  dom.deleteSelectedBtn.disabled = !visibleSelectedCount;
  dom.deleteAllBtn.disabled = !totalMessages;

  const selectPageLabel = dom.selectPageBtn.querySelector('span');
  if (selectPageLabel) {
    selectPageLabel.textContent = visibleCount && visibleSelectedCount === visibleCount ? 'Bỏ chọn trang' : 'Chọn trang';
  }

  const deleteSelectedLabel = dom.deleteSelectedBtn.querySelector('span');
  if (deleteSelectedLabel) {
    deleteSelectedLabel.textContent = visibleSelectedCount > 0 ? `Xóa đã chọn (${visibleSelectedCount})` : 'Xóa đã chọn';
  }

  dom.selectionSummary.textContent = visibleSelectedCount > 0 ? `${visibleSelectedCount} chọn` : `${totalMessages} email`;
}

function renderPagination() {
  const total = state.messages.length;
  const totalPages = getTotalPages();

  if (total === 0) {
    dom.paginationInfo.textContent = '0 / 0 email';
    dom.paginationControls.innerHTML = `
      <button class="pagination-btn" type="button" disabled>Trước</button>
      <button class="pagination-btn" type="button" disabled>Sau</button>
    `;
    return;
  }

  const start = (state.currentPage - 1) * MESSAGES_PER_PAGE + 1;
  const end = Math.min(state.currentPage * MESSAGES_PER_PAGE, total);
  dom.paginationInfo.textContent = `${start}-${end} / ${total} email`;

  const pageNumbers = buildPageNumbers(totalPages, state.currentPage);
  const buttons = [
    `<button class="pagination-btn" type="button" data-page-nav="prev" ${state.currentPage === 1 ? 'disabled' : ''}>Trước</button>`,
    ...pageNumbers.map((page) => (
      page === 'ellipsis'
        ? '<span class="px-1 text-gray-300">...</span>'
        : `<button class="pagination-btn ${page === state.currentPage ? 'active' : ''}" type="button" data-page="${page}">${page}</button>`
    )),
    `<button class="pagination-btn" type="button" data-page-nav="next" ${state.currentPage === totalPages ? 'disabled' : ''}>Sau</button>`,
  ];

  dom.paginationControls.innerHTML = buttons.join('');
  dom.paginationControls.querySelectorAll('[data-page]').forEach((button) => {
    button.addEventListener('click', () => goToPage(Number(button.dataset.page)));
  });
  dom.paginationControls.querySelectorAll('[data-page-nav]').forEach((button) => {
    button.addEventListener('click', () => {
      const direction = button.dataset.pageNav;
      goToPage(direction === 'prev' ? state.currentPage - 1 : state.currentPage + 1);
    });
  });
}

function goToPage(page) {
  const nextPage = Math.max(1, Math.min(page, getTotalPages()));
  if (nextPage === state.currentPage) {
    return;
  }
  state.currentPage = nextPage;
  renderMessages();
  renderPagination();
  dom.emailList.scrollTo({ top: 0, behavior: 'smooth' });
}

function getVisibleMessages() {
  const start = (state.currentPage - 1) * MESSAGES_PER_PAGE;
  return state.messages.slice(start, start + MESSAGES_PER_PAGE);
}

function getVisibleMessageIds() {
  return getVisibleMessages().map((message) => message.id);
}

function getVisibleSelectedMessageIds() {
  const selectedIds = new Set(state.selectedMessageIds);
  return getVisibleMessageIds().filter((messageId) => selectedIds.has(messageId));
}

function getDeleteTargetIds(messageId) {
  const visibleSelectedIds = getVisibleSelectedMessageIds();
  if (visibleSelectedIds.length > 1 && visibleSelectedIds.includes(messageId)) {
    return visibleSelectedIds;
  }
  return [messageId];
}

function getRangeSelectionIds(messageId) {
  const visibleIds = getVisibleMessageIds();
  const anchorId = state.selectionAnchorMessageId && visibleIds.includes(state.selectionAnchorMessageId)
    ? state.selectionAnchorMessageId
    : state.selectedMessageId;

  if (!anchorId || !visibleIds.includes(anchorId)) {
    return [messageId];
  }

  const startIndex = visibleIds.indexOf(anchorId);
  const endIndex = visibleIds.indexOf(messageId);
  if (startIndex === -1 || endIndex === -1) {
    return [messageId];
  }

  const [from, to] = startIndex <= endIndex ? [startIndex, endIndex] : [endIndex, startIndex];
  return visibleIds.slice(from, to + 1);
}

function normalizeSelectedMessageIds(ids) {
  const uniqueIds = Array.from(new Set(ids.map(Number).filter(Boolean)));
  const visibleIdSet = new Set(uniqueIds);
  const orderedVisibleIds = getVisibleMessageIds().filter((messageId) => visibleIdSet.has(messageId));
  return orderedVisibleIds.length ? orderedVisibleIds : uniqueIds;
}

function isMessageSelected(messageId, recipientAddress = null) {
  if (!state.selectedMessageIds.includes(messageId)) {
    return false;
  }
  if (state.selectedMessageIds.length === 1 && recipientAddress) {
    return state.selectedRecipientAddress === recipientAddress;
  }
  return true;
}

function getTotalPages() {
  return Math.max(1, Math.ceil(state.messages.length / MESSAGES_PER_PAGE));
}

function ensureValidPage() {
  state.currentPage = Math.min(Math.max(1, state.currentPage), getTotalPages());
}

function buildPageNumbers(totalPages, currentPage) {
  if (totalPages <= 5) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  if (currentPage <= 3) {
    return [1, 2, 3, 4, 'ellipsis', totalPages];
  }
  if (currentPage >= totalPages - 2) {
    return [1, 'ellipsis', totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
  }
  return [1, 'ellipsis', currentPage - 1, currentPage, currentPage + 1, 'ellipsis', totalPages];
}

function isSentFolder() {
  return state.currentFilter === 'sent';
}

function isSentMessage(message) {
  return Boolean(message && message.kind === 'sent');
}

function formatAddressList(addresses, fallback = '-') {
  const values = Array.isArray(addresses) ? addresses : [];
  const normalized = values.map((item) => String(item || '').trim()).filter(Boolean);
  return normalized.length ? normalized.join(', ') : fallback;
}

function getAvatarPresentation(message) {
  const primaryAddress = isSentMessage(message)
    ? formatAddressList(message.to, message.from_email || '')
    : message.recipient_address;
  const aliasLocalPart = getAliasLocalPart(primaryAddress);
  const seed = `${primaryAddress || ''}|${message.from_email || ''}|${message.from_name || ''}|${message.kind || 'inbox'}`;
  const palette = AVATAR_PALETTES[Math.abs(hashCode(seed)) % AVATAR_PALETTES.length];
  return {
    background: palette.background,
    color: palette.color,
    label: (aliasLocalPart || message.from_name || message.from_email || '?').charAt(0).toUpperCase(),
  };
}

function getAliasLocalPart(address) {
  return String(address || '').split('@')[0] || '';
}

function hashCode(value) {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = ((hash << 5) - hash) + value.charCodeAt(index);
    hash |= 0;
  }
  return hash;
}

function copyText(value, successMessage) {
  navigator.clipboard.writeText(value).then(() => {
    showToast(successMessage);
  }).catch(() => {
    const temp = document.createElement('textarea');
    temp.value = value;
    document.body.appendChild(temp);
    temp.select();
    document.execCommand('copy');
    document.body.removeChild(temp);
    showToast(successMessage);
  });
}

function showToast(message) {
  dom.toastMsg.textContent = message;
  dom.toast.classList.add('toast-show');
  setTimeout(() => dom.toast.classList.remove('toast-show'), 2200);
}

function handleError(error) {
  if (error?.status === 401) {
    showToast('Phiên đăng nhập đã hết hạn');
    showLogin();
    return;
  }
  if (error?.status === 403) {
    window.location.replace('/user.html');
    return;
  }
  showToast(error.message || 'Đã có lỗi xảy ra');
}

async function api(url, options = {}) {
  const response = await fetch(url, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let detail = 'Request failed';
    const rawText = await response.text();
    if (rawText) {
      try {
        const payload = JSON.parse(rawText);
        detail = payload.detail || detail;
      } catch {
        detail = rawText;
      }
    }
    const normalizedDetail = String(detail).trim().toLowerCase();
    if (
      normalizedDetail.includes('<!doctype html')
      || normalizedDetail.includes('<html')
      || normalizedDetail.includes('</body>')
    ) {
      detail = 'Máy chủ tạm thời không phản hồi. Vui lòng thử lại.';
    }
    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }

  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return response.json();
  }
  return response.text();
}

function markRecentMessages(nextMessages) {
  const now = Date.now();
  nextMessages.forEach((message) => {
    if (!state.seenMessageIds[message.id]) {
      state.recentMessageIds[message.id] = now;
      state.seenMessageIds[message.id] = true;
    }
  });

  if (!state.hasLoadedMessages) {
    nextMessages.forEach((message) => {
      state.seenMessageIds[message.id] = true;
    });
    state.recentMessageIds = {};
  }

  pruneRecentMessageIds();
}

function pruneRecentMessageIds() {
  const cutoff = Date.now() - NEW_MESSAGE_HIGHLIGHT_MS;
  Object.keys(state.recentMessageIds).forEach((id) => {
    if (state.recentMessageIds[id] < cutoff) {
      delete state.recentMessageIds[id];
    }
  });
}

function isRecentMessage(messageId) {
  return Boolean(state.recentMessageIds[messageId]);
}

function updateRecentMessageDecorations() {
  dom.emailList?.querySelectorAll('[data-recent-message]').forEach((row) => {
    const messageId = Number(row.dataset.messageId);
    const isRecent = isRecentMessage(messageId);
    row.dataset.recentMessage = isRecent ? 'true' : 'false';
    row.classList.toggle('recent', isRecent);
    const badge = row.querySelector('.mail-badge-new');
    if (badge) {
      badge.classList.toggle('hidden', !isRecent);
    }
  });
}

function buildMessageListSignature(messages) {
  return messages.map((message) => [
    message.id,
    message.unread ? 1 : 0,
    message.important ? 1 : 0,
    message.recipient_address || '',
    message.from_name || '',
    message.from_email || '',
    message.subject || '',
    message.received_at || message.sent_at || '',
    message.kind || 'inbox',
    formatAddressList(message.to, ''),
    formatAddressList(message.cc, ''),
    message.has_otps ? 1 : (message.extracted_otps || []).length,
    message.has_links ? 1 : (message.extracted_links || []).length,
  ].join('|')).join('~');
}

function formatLanguageLabel(value) {
  const normalized = String(value || '').trim().toLowerCase();
  const labels = {
    auto: 'Auto',
    en: 'English',
    vi: 'Tiếng Việt',
    ja: 'Tiếng Nhật',
    ko: 'Tiếng Hàn',
    zh: 'Tiếng Trung',
    fr: 'Tiếng Pháp',
    de: 'Tiếng Đức',
    es: 'Tiếng Tây Ban Nha',
    ru: 'Tiếng Nga',
    th: 'Tiếng Thái',
  };
  return labels[normalized] || normalized.toUpperCase() || 'Auto';
}

function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function escapeAttribute(value) {
  return escapeHtml(value).replace(/`/g, '&#96;');
}

function linkifyText(value) {
  const escaped = escapeHtml(value);
  return escaped.replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" class="text-lush-500 hover:underline break-all" target="_blank" rel="noreferrer">$1</a>');
}

function buildEmailFrameDocument(htmlBody) {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <base target="_blank">
  <style>
    html, body { margin: 0; padding: 0; background: #ffffff; }
    body { overflow-wrap: anywhere; word-break: break-word; }
    img, video { max-width: 100% !important; height: auto !important; }
    table { max-width: 100% !important; }
  </style>
</head>
<body>${sanitizeEmailHtml(htmlBody)}</body>
</html>`;
}

function sanitizeEmailHtml(value) {
  return String(value || '')
    .replace(/<script\b[\s\S]*?<\/script>/gi, '')
    .replace(/<base\b[^>]*>/gi, '')
    .replace(/\son[a-z]+\s*=\s*(['"]).*?\1/gi, '')
    .replace(/\son[a-z]+\s*=\s*[^\s>]+/gi, '')
    .replace(/\s(href|src)\s*=\s*(['"])\s*javascript:[\s\S]*?\2/gi, ' $1="#"');
}

function syncEmailFrameHeights() {
  document.querySelectorAll('iframe[data-email-frame="true"]').forEach((frame) => {
    const applyHeight = () => {
      try {
        const doc = frame.contentDocument;
        if (!doc) {
          return;
        }
        const bodyHeight = doc.body ? doc.body.scrollHeight : 0;
        const htmlHeight = doc.documentElement ? doc.documentElement.scrollHeight : 0;
        frame.style.height = `${Math.max(bodyHeight, htmlHeight, 240)}px`;
      } catch {
        frame.style.height = '420px';
      }
    };

    frame.addEventListener('load', applyHeight, { once: true });
    window.setTimeout(applyHeight, 60);
  });
}

function formatFileSize(sizeBytes) {
  const size = Number(sizeBytes || 0);
  if (!size) {
    return '0 B';
  }
  const units = ['B', 'KB', 'MB', 'GB'];
  let value = size;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  const digits = value >= 10 || unitIndex === 0 ? 0 : 1;
  return `${value.toFixed(digits)} ${units[unitIndex]}`;
}

function formatRelativeDate(dateStr) {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now - date;
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return 'Vừa xong';
  if (minutes < 60) return `${minutes} phút trước`;
  if (hours < 24) return `${hours} giờ trước`;
  if (days < 7) return `${days} ngày trước`;
  return date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
}

function formatFullDate(dateStr) {
  return new Date(dateStr).toLocaleString('vi-VN', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}
