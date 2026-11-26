const state = { user: null, csrf: null, assignments: [], activeView: "overview" };
const app = document.querySelector("#app");
const toast = document.querySelector("#toast");
const esc = (value = "") => String(value).replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
const dateLabel = value => new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit", timeZone: "Asia/Kolkata" }).format(new Date(value));
const dueShort = value => new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", timeZone: "Asia/Kolkata" }).format(new Date(value));
const isPast = value => new Date(value).getTime() < Date.now();
const initials = name => name.split(/\s+/).slice(0, 2).map(part => part[0]).join("").toUpperCase();

async function api(url, options = {}) {
  const headers = { ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }), ...(options.headers || {}) };
  if (state.csrf && options.method && options.method !== "GET") headers["X-CSRF-Token"] = state.csrf;
  const response = await fetch(url, { credentials: "same-origin", ...options, headers });
  const data = response.headers.get("content-type")?.includes("application/json") ? await response.json() : null;
  if (!response.ok) throw new Error(data?.error || "Something went wrong. Please try again.");
  return data;
}

function notify(message, error = false) {
  toast.textContent = message;
  toast.classList.toggle("toast-error", error);
  toast.classList.add("toast-visible");
  clearTimeout(notify.timeout);
  notify.timeout = setTimeout(() => toast.classList.remove("toast-visible"), 3200);
}

function loginMarkup() {
  return `<section class="login-layout">
    <div class="login-art"><div class="brand brand-light"><span class="brand-mark">B</span><span>BMSIT <small>COMPUTER SCIENCE & ENGINEERING</small></span></div><div class="art-copy"><div class="eyebrow light-eyebrow"><span></span> DEPARTMENT OF CSE</div><h1>Good work<br>deserves a <em>better<br>workflow.</em></h1><p>One place for assignments, submissions and feedback. Spend less time coordinating — and more time learning.</p></div><div class="art-foot"><span>ASSIGNMENT PORTAL</span><span>01 — 26</span></div><div class="art-orbit orbit-one"></div><div class="art-orbit orbit-two"></div></div>
    <div class="login-panel"><div class="mobile-brand brand"><span class="brand-mark">B</span><span>BMSIT <small>COMPUTER SCIENCE & ENGINEERING</small></span></div><div class="login-box"><div class="eyebrow"><span></span> YOUR ACADEMIC WORKSPACE</div><h2>Welcome back</h2><p class="muted">Sign in with your college account to continue.</p>
      <form id="login-form"><label for="email">College email</label><div class="input-wrap"><span class="input-icon">＠</span><input id="email" name="email" type="email" autocomplete="username" placeholder="name@bmsit.edu" required></div><div class="label-row"><label for="password">Password</label><span class="field-hint">Secure sign in</span></div><div class="input-wrap"><span class="input-icon">⌑</span><input id="password" name="password" type="password" autocomplete="current-password" placeholder="Enter your password" required><button class="password-toggle" type="button" aria-label="Show password">Show</button></div><button class="button button-primary login-button" type="submit">Sign in <span>→</span></button><div id="login-error" class="form-error" role="alert"></div></form>
      <div class="demo-box"><div class="demo-top"><span class="demo-dot"></span> DEMO ACCESS</div><div class="demo-accounts"><button data-demo="student@bmsit.edu|Student123!"><b>Student</b><span>student@bmsit.edu</span></button><button data-demo="professor@bmsit.edu|Professor123!"><b>Professor</b><span>professor@bmsit.edu</span></button><button data-demo="admin@bmsit.edu|Admin123!"><b>Admin</b><span>admin@bmsit.edu</span></button></div></div><div class="login-footer"><span>© 2026 BMSIT CSE</span><span>Built for better learning <i>✳</i></span></div>
    </div></div></section>`;
}

function bindLogin() {
  document.querySelector("#login-form").addEventListener("submit", async event => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const error = document.querySelector("#login-error");
    const button = event.currentTarget.querySelector("button[type=submit]");
    button.disabled = true;
    error.textContent = "";
    try {
      const result = await api("/api/auth/login", { method: "POST", body: JSON.stringify({ email: form.get("email"), password: form.get("password") }) });
      state.user = result.user;
      state.csrf = result.csrf_token;
      await renderDashboard();
    } catch (reason) { error.textContent = reason.message; }
    finally { button.disabled = false; }
  });
  document.querySelectorAll("[data-demo]").forEach(button => button.addEventListener("click", () => {
    const [email, password] = button.dataset.demo.split("|");
    document.querySelector("#email").value = email;
    document.querySelector("#password").value = password;
    document.querySelector("#login-form").requestSubmit();
  }));
  document.querySelector(".password-toggle").addEventListener("click", event => {
    const input = document.querySelector("#password");
    input.type = input.type === "password" ? "text" : "password";
    event.currentTarget.textContent = input.type === "password" ? "Show" : "Hide";
  });
}

function showLogin() {
  app.innerHTML = loginMarkup();
  bindLogin();
}

function shell(content, active = "overview") {
  const roleLabel = { student: "Student", professor: "Professor", admin: "Administrator" }[state.user.role];
  const links = state.user.role === "student"
    ? [["overview", "▦", "Overview"], ["assignments", "▤", "Assignments"], ["notifications", "◌", "Notifications"]]
    : state.user.role === "professor"
      ? [["overview", "▦", "Overview"], ["assignments", "▤", "Assignments"], ["submissions", "▣", "Submissions"], ["notifications", "◌", "Notifications"]]
      : [["overview", "▦", "Overview"], ["users", "♙", "User accounts"]];
  app.innerHTML = `<div class="workspace"><aside class="sidebar"><div class="brand side-brand"><span class="brand-mark">B</span><span>BMSIT <small>CSE · ASSIGNMENT PORTAL</small></span></div><div class="side-section">WORKSPACE</div><nav>${links.map(([id, icon, label]) => `<button class="nav-link ${id === active ? "active" : ""}" data-view="${id}"><span class="nav-icon">${icon}</span>${label}${id === "notifications" ? '<span class="nav-dot"></span>' : ""}</button>`).join("")}</nav><div class="sidebar-bottom"><div class="help-card"><span>✳</span><b>Need a hand?</b><p>Reach out to your department coordinator for help.</p></div><button class="nav-link" data-view="profile"><span class="nav-icon">◎</span>My profile</button><button class="nav-link logout-link" id="logout"><span class="nav-icon">↪</span>Sign out</button></div></aside><section class="main-area"><header class="topbar"><div class="mobile-title"><span class="brand-mark">B</span> BMSIT <span class="crumb">/ ${roleLabel}</span></div><div class="topbar-right"><span class="semester-tag">${state.user.role === "student" ? `SEMESTER ${state.user.semester} · SECTION ${esc(state.user.section)}` : "CSE DEPARTMENT"}</span><button class="icon-button notification-button" data-view="notifications" aria-label="Notifications">♧<i></i></button><div class="user-menu"><div class="avatar">${esc(initials(state.user.name))}</div><div class="user-meta"><b>${esc(state.user.name)}</b><span>${roleLabel}</span></div></div></div></header><main class="content" id="view-content">${content}</main><footer class="workspace-footer"><span>BMSIT · DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING</span><span>ASSIGNMENT PORTAL <i>✳</i></span></footer></section></div>`;
  document.querySelectorAll("[data-view]").forEach(button => button.addEventListener("click", () => navigate(button.dataset.view)));
  document.querySelector("#logout").addEventListener("click", logout);
}

function metricCard(label, value, note, icon, accent = "") {
  return `<article class="metric-card"><div class="metric-top"><span>${label}</span><span class="metric-icon ${accent}">${icon}</span></div><strong>${value}</strong><small>${note}</small></article>`;
}

function sectionHeading(eyebrow, title, description, action = "") {
  return `<div class="page-heading"><div><div class="eyebrow"><span></span> ${eyebrow}</div><h1>${title}</h1><p>${description}</p></div>${action}</div>`;
}

function statusPill(status) {
  const style = status === "published" || status === "submitted" || status === "resubmitted" ? "green" : status === "late" ? "amber" : status === "draft" ? "gray" : "blue";
  return `<span class="status-pill ${style}"><i></i>${esc(status.replace("_", " "))}</span>`;
}

function assignmentRows(assignments, professor = false) {
  if (!assignments.length) return `<div class="empty-state"><div>▤</div><b>No assignments yet</b><p>When assignments are available, they’ll show up here.</p></div>`;
  return assignments.map(item => `<div class="assignment-row"><div class="subject-icon">${esc(item.subject.split(/\s+/).map(word => word[0]).slice(0, 2).join(""))}</div><div class="assignment-info"><b>${esc(item.title)}</b><span>${esc(item.subject)} <i>·</i> Sem ${item.semester} / ${esc(item.section)}</span></div><div class="deadline-info"><span>${professor ? `${item.submission_count || 0} submissions` : `Due ${dueShort(item.due_at)}`}</span><small>${professor ? `${item.reviewed_count || 0} reviewed` : `${item.max_marks} marks`}</small></div><div class="row-status">${statusPill(professor ? item.status : (item.submission_status || (isPast(item.due_at) ? "missed" : "not submitted")))}</div><button class="row-arrow" data-open="${item.id}" aria-label="Open ${esc(item.title)}">↗</button></div>`).join("");
}

async function loadAssignments() {
  const path = state.user.role === "student" ? "/api/student/assignments" : "/api/professor/assignments";
  state.assignments = (await api(path)).assignments;
}

async function renderDashboard(view = "overview") {
  state.activeView = view;
  if (state.user.role === "student") await loadAssignments();
  if (state.user.role === "professor") await loadAssignments();
  let content = "";
  if (view === "overview") content = await overviewView();
  else if (view === "assignments") content = assignmentsView();
  else if (view === "submissions") content = submissionsView();
  else if (view === "notifications") content = await notificationsView();
  else if (view === "users") content = await usersView();
  else if (view === "profile") content = profileView();
  shell(content, view);
  bindViewActions();
}

async function overviewView() {
  if (state.user.role === "student") {
    const assignments = state.assignments;
    const submitted = assignments.filter(a => a.submission_id).length;
    const graded = assignments.filter(a => a.result_published).length;
    const dueSoon = assignments.filter(a => !a.submission_id && !isPast(a.due_at) && new Date(a.due_at).getTime() - Date.now() < 7 * 86400000).length;
    return `${sectionHeading("STUDENT WORKSPACE", `Good ${new Date().getHours() < 12 ? "morning" : "afternoon"}, ${esc(state.user.name.split(" ")[0])} <span class="wave">✳</span>`, "Here’s what’s happening with your coursework today.", '<button class="button button-primary" data-view="assignments">Browse assignments <span>→</span></button>')}
      <div class="metrics-grid">${metricCard("Active assignments", assignments.length - submitted, "Ready for your attention", "▤", "mint")}${metricCard("Due this week", dueSoon, "Keep an eye on these", "◷", "gold")}${metricCard("Submitted", submitted, "Your work is in", "↗", "blue")}${metricCard("Results released", graded, "Feedback is waiting", "✳", "lavender")}</div>
      <div class="overview-grid"><section class="panel assignment-panel"><div class="panel-heading"><div><div class="eyebrow">YOUR COURSEWORK</div><h2>Recent assignments</h2></div><button class="text-button" data-view="assignments">View all <span>→</span></button></div><div class="assignment-list">${assignmentRows(assignments.slice(0, 5))}</div></section><aside class="panel side-panel"><div class="eyebrow">YOUR SEMESTER</div><h2>Keep moving<br>forward.</h2><p>You’re viewing work for Semester ${state.user.semester}, Section ${esc(state.user.section)}. Stay ahead of the next deadline.</p><div class="semester-progress"><div><span>Work submitted</span><b>${assignments.length ? Math.round(submitted / assignments.length * 100) : 0}%</b></div><div class="progress-track"><span style="width:${assignments.length ? submitted / assignments.length * 100 : 0}%"></span></div></div><div class="side-note"><span>✳</span><span>Tip: your results are only visible once your professor publishes them.</span></div></aside></div>`;
  }
  if (state.user.role === "professor") {
    const assignments = state.assignments;
    const submissions = assignments.reduce((sum, a) => sum + Number(a.submission_count || 0), 0);
    const reviewed = assignments.reduce((sum, a) => sum + Number(a.reviewed_count || 0), 0);
    return `${sectionHeading("FACULTY WORKSPACE", `Welcome, ${esc(state.user.name.replace(/^Prof\\.\\s*/, "").split(" ")[0])} <span class="wave">✳</span>`, "Your classes, assignments and student work — all in one place.", '<button class="button button-primary" id="create-assignment">＋ New assignment</button>')}
      <div class="metrics-grid">${metricCard("Published", assignments.filter(a => a.status === "published").length, "Across your classes", "▤", "mint")}${metricCard("Submissions", submissions, "Student work received", "↙", "blue")}${metricCard("To review", Math.max(submissions - reviewed, 0), "Waiting for your feedback", "◷", "gold")}${metricCard("Reviewed", reviewed, "Results published", "✳", "lavender")}</div>
      <div class="overview-grid"><section class="panel assignment-panel"><div class="panel-heading"><div><div class="eyebrow">TEACHING OVERVIEW</div><h2>Your assignments</h2></div><button class="text-button" data-view="assignments">Manage all <span>→</span></button></div><div class="assignment-list">${assignmentRows(assignments.slice(0, 5), true)}</div></section><aside class="panel side-panel professor-side"><div class="eyebrow">YOUR TEACHING</div><h2>Great teaching<br>starts here.</h2><p>Create a task for your class, review submitted work, then release results when you’re ready.</p><button class="button button-secondary" id="create-assignment-side">＋ Create an assignment</button><div class="side-note"><span>✳</span><span>Students only see grades after you publish the result.</span></div></aside></div>`;
  }
  const { counts } = await api("/api/admin/overview");
  return `${sectionHeading("ADMINISTRATION", "Department overview <span class=\"wave\">✳</span>", "A clear view of your academic community and assignment activity.", '<button class="button button-primary" data-view="users">Manage accounts <span>→</span></button>')}
    <div class="metrics-grid">${metricCard("Students", counts.students, "Active student accounts", "♙", "mint")}${metricCard("Professors", counts.professors, "Faculty accounts", "♧", "blue")}${metricCard("Subjects", counts.subjects, "Mapped to teaching staff", "▧", "gold")}${metricCard("Sections", counts.sections, "Across semesters", "▦", "lavender")}</div>
    <div class="overview-grid"><section class="panel admin-summary"><div class="eyebrow">SYSTEM ACTIVITY</div><h2>Assignment activity</h2><div class="admin-counts"><div><strong>${counts.assignments}</strong><span>Assignments</span></div><div><strong>${counts.submissions}</strong><span>Submissions</span></div></div><p>Manage accounts and keep the department’s academic records up to date.</p><button class="button button-secondary" data-view="users">View user accounts →</button></section><aside class="panel side-panel"><div class="eyebrow">ADMIN ACCESS</div><h2>One department.<br>One source of truth.</h2><p>Account access can be managed centrally. Academic mappings are provisioned by the department.</p><div class="side-note"><span>✳</span><span>Keep academic records accurate to ensure students see the right work.</span></div></aside></div>`;
}

function assignmentsView() {
  const professor = state.user.role === "professor";
  return `${sectionHeading(professor ? "ASSIGNMENT MANAGEMENT" : "YOUR COURSEWORK", professor ? "Assignments" : "All assignments", professor ? "Create, publish and keep track of work for your classes." : "All the work assigned to your classes, in one place.", professor ? '<button class="button button-primary" id="create-assignment">＋ New assignment</button>' : "")}
    <section class="panel full-list-panel"><div class="panel-heading"><div><div class="eyebrow">${professor ? "YOUR CLASSES" : "SUBJECTS & DEADLINES"}</div><h2>${professor ? "Assignment list" : `${state.assignments.length} assignments`}</h2></div><div class="list-tools"><span class="search-wrap"><span>⌕</span><input id="assignment-search" type="search" placeholder="Search assignments"></span><select id="assignment-filter" aria-label="Filter assignments"><option value="all">All status</option><option value="submitted">Submitted</option><option value="pending">Not submitted</option><option value="published">Published</option><option value="draft">Draft</option></select></div></div><div class="assignment-list" id="assignment-list">${assignmentRows(state.assignments, professor)}</div></section>`;
}

function submissionsView() {
  return `${sectionHeading("STUDENT WORK", "Submission queue", "Choose an assignment to review the latest work from your students.")}
    <section class="panel full-list-panel"><div class="panel-heading"><div><div class="eyebrow">YOUR ASSIGNMENTS</div><h2>Pick an assignment</h2></div></div><div class="assignment-list">${assignmentRows(state.assignments.filter(a => a.status !== "draft"), true)}</div></section>`;
}

async function notificationsView() {
  const { notifications } = await api("/api/notifications");
  const items = notifications.length ? notifications.map(item => `<div class="notification-row"><div class="notification-icon">✳</div><div><b>${esc(item.title)}</b><p>${esc(item.message)}</p><span>${dateLabel(item.created_at)}</span></div></div>`).join("") : `<div class="empty-state"><div>◌</div><b>You’re all caught up</b><p>New assignment and result updates will appear here.</p></div>`;
  return `${sectionHeading("UPDATES", "Notifications", "The latest assignment and result updates for your account.")}<section class="panel notification-panel"><div class="panel-heading"><div><div class="eyebrow">RECENT ACTIVITY</div><h2>Your updates</h2></div></div>${items}</section>`;
}

async function usersView() {
  const [{ users }, { mappings }] = await Promise.all([api("/api/admin/users"), api("/api/admin/mappings")]);
  return `${sectionHeading("ACCOUNT MANAGEMENT", "User accounts", "Manage access for students, professors and administrators.", '<button class="button button-primary" id="add-user">＋ Add account</button>')}<section class="panel full-list-panel"><div class="panel-heading"><div><div class="eyebrow">DEPARTMENT DIRECTORY</div><h2>${users.length} accounts</h2></div></div><div class="table-wrap"><table><thead><tr><th>NAME</th><th>EMAIL</th><th>ROLE</th><th>CLASS / ID</th><th>STATUS</th><th></th></tr></thead><tbody>${users.map(user => `<tr><td><div class="table-user"><span class="avatar small-avatar">${esc(initials(user.name))}</span><b>${esc(user.name)}</b></div></td><td>${esc(user.email)}</td><td><span class="role-tag">${esc(user.role)}</span></td><td>${esc(user.usn || (user.semester ? `Sem ${user.semester} · ${user.section}` : "—"))}</td><td>${statusPill(user.active ? "active" : "inactive")}</td><td>${user.id !== state.user.id ? `<button class="table-action" data-toggle-user="${user.id}" data-active="${user.active}">${user.active ? "Deactivate" : "Activate"}</button>` : "You"}</td></tr>`).join("")}</tbody></table></div></section><section class="panel full-list-panel mapping-panel"><div class="panel-heading"><div><div class="eyebrow">ACADEMIC ACCESS</div><h2>Subject & class mappings</h2></div><button class="button button-secondary" id="add-mapping">＋ Add mapping</button></div><div class="table-wrap"><table><thead><tr><th>ACCOUNT</th><th>ROLE</th><th>SUBJECT</th><th>SEMESTER</th><th>SECTION</th><th></th></tr></thead><tbody>${mappings.map(mapping => `<tr><td>${esc(mapping.name)}</td><td><span class="role-tag">${esc(mapping.role)}</span></td><td>${esc(mapping.subject)}</td><td>${mapping.semester}</td><td>${esc(mapping.section)}</td><td><button class="table-action" data-remove-mapping="${mapping.user_id}" data-subject="${esc(mapping.subject)}" data-semester="${mapping.semester}" data-section="${esc(mapping.section)}">Remove</button></td></tr>`).join("") || '<tr><td colspan="6">No class mappings yet.</td></tr>'}</tbody></table></div></section>`;
}

function profileView() {
  return `${sectionHeading("YOUR ACCOUNT", "My profile", "Your BMSIT CSE account information.")}<section class="panel profile-card"><div class="profile-avatar">${esc(initials(state.user.name))}</div><div><div class="eyebrow">ACCOUNT DETAILS</div><h2>${esc(state.user.name)}</h2><p>${esc(state.user.email)}</p><span class="role-tag">${esc(state.user.role)}</span>${state.user.role === "student" ? `<div class="profile-class">Semester ${state.user.semester} <span>·</span> Section ${esc(state.user.section)}</div>` : ""}</div></section>`;
}

function bindViewActions() {
  document.querySelectorAll("#create-assignment, #create-assignment-side").forEach(button => button.addEventListener("click", openCreateDialog));
  document.querySelectorAll("[data-open]").forEach(button => button.addEventListener("click", () => openAssignment(button.dataset.open)));
  document.querySelectorAll("[data-view]").forEach(button => button.addEventListener("click", () => navigate(button.dataset.view)));
  const search = document.querySelector("#assignment-search");
  if (search) search.addEventListener("input", filterAssignments);
  const filter = document.querySelector("#assignment-filter");
  if (filter) filter.addEventListener("change", filterAssignments);
  document.querySelector("#add-user")?.addEventListener("click", openUserDialog);
  document.querySelector("#add-mapping")?.addEventListener("click", openMappingDialog);
  document.querySelectorAll("[data-toggle-user]").forEach(button => button.addEventListener("click", async () => {
    try { await api(`/api/admin/users/${button.dataset.toggleUser}/status`, { method: "PATCH", body: JSON.stringify({ active: button.dataset.active !== "1" }) }); notify("Account status updated."); await navigate("users"); }
    catch (error) { notify(error.message, true); }
  }));
  document.querySelectorAll("[data-remove-mapping]").forEach(button => button.addEventListener("click", async () => {
    const mapping = { user_id: Number(button.dataset.removeMapping), subject: button.dataset.subject, semester: Number(button.dataset.semester), section: button.dataset.section };
    try { await api("/api/admin/mappings", { method: "DELETE", body: JSON.stringify(mapping) }); notify("Subject mapping removed."); await navigate("users"); }
    catch (error) { notify(error.message, true); }
  }));
}

function filterAssignments() {
  const query = document.querySelector("#assignment-search")?.value.toLowerCase() || "";
  const filter = document.querySelector("#assignment-filter")?.value || "all";
  let filtered = state.assignments.filter(item => `${item.title} ${item.subject}`.toLowerCase().includes(query));
  if (filter === "submitted") filtered = filtered.filter(a => a.submission_id);
  if (filter === "pending") filtered = filtered.filter(a => !a.submission_id);
  if (filter === "published" || filter === "draft") filtered = filtered.filter(a => a.status === filter);
  document.querySelector("#assignment-list").innerHTML = assignmentRows(filtered, state.user.role === "professor");
  document.querySelectorAll("[data-open]").forEach(button => button.addEventListener("click", () => openAssignment(button.dataset.open)));
}

async function openCreateDialog() {
  const dialog = document.querySelector("#assignment-dialog");
  document.querySelector("#dialog-content").innerHTML = `<div class="eyebrow"><span></span> NEW COURSEWORK</div><h2>Create an assignment</h2><p class="muted">Add the details now. You can save a draft and publish when you’re ready.</p><form id="create-form" class="dialog-form"><label>Title<input name="title" maxlength="160" placeholder="e.g. Graph Algorithms" required></label><div class="form-two"><label>Subject<select name="subject" required>${["Data Structures", "Database Systems", "Web Technology", "Operating Systems"].map(s => `<option>${s}</option>`).join("")}</select></label><label>Semester<select name="semester">${Array.from({ length: 8 }, (_, i) => `<option value="${i + 1}" ${i === 2 ? "selected" : ""}>Semester ${i + 1}</option>`).join("")}</select></label></div><div class="form-two"><label>Section<input name="section" value="A" maxlength="10" required></label><label>Maximum marks<input name="max_marks" type="number" min="1" max="1000" value="20" required></label></div><label>Instructions<textarea name="description" rows="4" placeholder="What should students do?" required></textarea></label><div class="form-two"><label>Deadline (IST)<input name="due_at" type="datetime-local" required></label><label class="checkbox-label"><input name="allow_resubmissions" type="checkbox" checked> Allow resubmissions</label></div><div class="dialog-actions"><button type="button" class="button button-quiet" data-close>Cancel</button><button type="submit" class="button button-secondary">Save draft</button><button type="submit" class="button button-primary" name="publish" value="yes">Publish now <span>→</span></button></div><div class="form-error" id="dialog-error"></div></form>`;
  dialog.showModal();
  document.querySelector("[data-close]").addEventListener("click", () => dialog.close());
  document.querySelector("#create-form").addEventListener("submit", async event => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const data = Object.fromEntries(form.entries());
    data.allow_resubmissions = form.has("allow_resubmissions");
    data.semester = Number(data.semester);
    data.max_marks = Number(data.max_marks);
    try {
      const created = await api("/api/professor/assignments", { method: "POST", body: JSON.stringify(data) });
      if (event.submitter?.name === "publish") await api(`/api/assignments/${created.id}/publish`, { method: "POST", body: "{}" });
      dialog.close(); notify(event.submitter?.name === "publish" ? "Assignment published." : "Draft saved.");
      await navigate("assignments");
    } catch (error) { document.querySelector("#dialog-error").textContent = error.message; }
  });
}

async function openAssignment(id) {
  try {
    const data = await api(`/api/assignments/${id}`);
    const assignment = data.assignment;
    if (state.user.role === "professor") return openProfessorAssignment(assignment);
    const studentItem = state.assignments.find(item => item.id === Number(id));
    const dialog = document.querySelector("#assignment-dialog");
    document.querySelector("#dialog-content").innerHTML = `<div class="eyebrow"><span></span> ${esc(assignment.subject.toUpperCase())} · SEMESTER ${assignment.semester}</div><h2>${esc(assignment.title)}</h2><p class="assignment-description">${esc(assignment.description)}</p><div class="detail-grid"><div><span>DEADLINE</span><b>${dateLabel(assignment.due_at)} IST</b></div><div><span>MAXIMUM MARKS</span><b>${assignment.max_marks} marks</b></div><div><span>PROFESSOR</span><b>${esc((studentItem && studentItem.professor) || "CSE Faculty")}</b></div><div><span>SUBMISSION</span><b>${studentItem?.submission_status ? esc(studentItem.submission_status) : "Not submitted"}</b></div></div>${studentItem?.result_published ? `<div class="result-card"><span>YOUR RESULT</span><strong>${studentItem.marks} <small>/ ${assignment.max_marks}</small></strong><p>${esc(studentItem.feedback || "No written feedback.")}</p></div>` : studentItem?.submission_id ? `<div class="info-banner">Your work has been submitted. Your result will appear here once it’s published.</div>` : `<form id="submission-form" class="upload-box"><label for="submission-file" class="upload-label"><span class="upload-symbol">↑</span><b>Upload your work</b><span>PDF, DOCX, PPTX or ZIP · up to 10 MB</span><input id="submission-file" type="file" name="file" accept=".pdf,.docx,.pptx,.zip" required></label><button class="button button-primary" type="submit">Submit assignment <span>→</span></button><div id="upload-error" class="form-error"></div></form>`}`;
    dialog.showModal();
    if (!studentItem?.submission_id) document.querySelector("#submission-form").addEventListener("submit", async event => {
      event.preventDefault();
      const button = event.currentTarget.querySelector("button");
      button.disabled = true;
      try {
        const result = await api(`/api/assignments/${id}/submissions`, { method: "POST", body: new FormData(event.currentTarget) });
        dialog.close(); notify(`Submission received · ${result.status}`); await renderDashboard(state.activeView);
      } catch (error) { document.querySelector("#upload-error").textContent = error.message; }
      finally { button.disabled = false; }
    });
  } catch (error) { notify(error.message, true); }
}

async function openProfessorAssignment(assignment) {
  const { submissions } = await api(`/api/professor/assignments/${assignment.id}/submissions`);
  const dialog = document.querySelector("#assignment-dialog");
  const list = submissions.length ? submissions.map(item => `<div class="submission-card"><div class="submission-student"><div class="avatar small-avatar">${esc(initials(item.student_name))}</div><div><b>${esc(item.student_name)}</b><span>${esc(item.usn || "")} · ${dateLabel(item.submitted_at)}</span></div></div><div class="submission-file"><span>▧</span><span>${esc(item.original_name)}<small>${(item.size / 1024).toFixed(0)} KB · ${esc(item.status)}</small></span><a class="download-link" href="/api/submissions/${item.id}/download">↓</a></div><form class="grade-form" data-grade="${item.id}"><label>Marks (out of ${assignment.max_marks})<input type="number" min="0" max="${assignment.max_marks}" step="0.5" name="marks" value="${item.marks ?? ""}" required></label><label>Feedback<textarea name="feedback" rows="2" maxlength="5000">${esc(item.feedback || "")}</textarea></label><div class="grade-actions"><button class="button button-secondary" type="submit">Save evaluation</button>${item.published_at ? '<span class="published-note">Result published</span>' : `<button class="text-button publish-result" type="button" data-publish-result="${item.id}">Publish result →</button>`}</div></form></div>`).join("") : `<div class="empty-state"><div>↙</div><b>No submissions yet</b><p>Student work will appear here after it’s submitted.</p></div>`;
  document.querySelector("#dialog-content").innerHTML = `<div class="eyebrow"><span></span> ${esc(assignment.subject.toUpperCase())} · SEM ${assignment.semester} / ${esc(assignment.section)}</div><h2>${esc(assignment.title)}</h2><p class="muted">${esc(assignment.description)}</p><div class="submission-list">${list}</div>`;
  dialog.showModal();
  document.querySelectorAll("[data-grade]").forEach(form => form.addEventListener("submit", async event => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(form).entries());
    try { await api(`/api/professor/submissions/${form.dataset.grade}/grade`, { method: "POST", body: JSON.stringify(data) }); notify("Evaluation saved as a draft."); }
    catch (error) { notify(error.message, true); }
  }));
  document.querySelectorAll("[data-publish-result]").forEach(button => button.addEventListener("click", async () => {
    try { await api(`/api/professor/submissions/${button.dataset.publishResult}/publish-result`, { method: "POST", body: "{}" }); notify("Result published to the student."); await openProfessorAssignment(assignment); }
    catch (error) { notify(error.message, true); }
  }));
}

function openUserDialog() {
  const dialog = document.querySelector("#assignment-dialog");
  document.querySelector("#dialog-content").innerHTML = `<div class="eyebrow"><span></span> ACCOUNT MANAGEMENT</div><h2>Add an account</h2><p class="muted">Create a department account. Use a temporary password and share it securely.</p><form id="user-form" class="dialog-form"><label>Full name<input name="name" required maxlength="120"></label><label>College email<input name="email" type="email" required></label><div class="form-two"><label>Role<select name="role"><option value="student">Student</option><option value="professor">Professor</option><option value="admin">Administrator</option></select></label><label>Temporary password<input name="password" type="password" minlength="10" required></label></div><div class="form-two"><label>USN (students)<input name="usn"></label><label>Semester<input name="semester" type="number" min="1" max="8"></label></div><label>Section (students)<input name="section"></label><div class="dialog-actions"><button class="button button-quiet" type="button" data-close>Cancel</button><button class="button button-primary" type="submit">Create account →</button></div><div class="form-error" id="dialog-error"></div></form>`;
  dialog.showModal();
  document.querySelector("[data-close]").addEventListener("click", () => dialog.close());
  document.querySelector("#user-form").addEventListener("submit", async event => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget).entries());
    if (data.semester) data.semester = Number(data.semester);
    try { await api("/api/admin/users", { method: "POST", body: JSON.stringify(data) }); dialog.close(); notify("Account created."); await navigate("users"); }
    catch (error) { document.querySelector("#dialog-error").textContent = error.message; }
  });
}

async function openMappingDialog() {
  try {
    const { users } = await api("/api/admin/users");
    const eligible = users.filter(user => user.active && user.role !== "admin");
    if (!eligible.length) { notify("Create a student or professor account before adding a mapping.", true); return; }
    const dialog = document.querySelector("#assignment-dialog");
    document.querySelector("#dialog-content").innerHTML = `<div class="eyebrow"><span></span> ACADEMIC ACCESS</div><h2>Add a subject mapping</h2><p class="muted">Map an active student or professor to the correct subject and class.</p><form id="mapping-form" class="dialog-form"><label>Account<select name="user_id" required>${eligible.map(user => `<option value="${user.id}">${esc(user.name)} · ${esc(user.role)} · ${esc(user.email)}</option>`).join("")}</select></label><label>Subject<select name="subject" required>${["Data Structures", "Database Systems", "Web Technology", "Operating Systems"].map(subject => `<option>${subject}</option>`).join("")}</select></label><div class="form-two"><label>Semester<select name="semester">${Array.from({ length: 8 }, (_, i) => `<option value="${i + 1}" ${i === 2 ? "selected" : ""}>Semester ${i + 1}</option>`).join("")}</select></label><label>Section<input name="section" value="A" maxlength="10" required></label></div><div class="dialog-actions"><button class="button button-quiet" type="button" data-close>Cancel</button><button class="button button-primary" type="submit">Save mapping →</button></div><div class="form-error" id="dialog-error"></div></form>`;
    dialog.showModal();
    document.querySelector("[data-close]").addEventListener("click", () => dialog.close());
    document.querySelector("#mapping-form").addEventListener("submit", async event => {
      event.preventDefault();
      const data = Object.fromEntries(new FormData(event.currentTarget).entries());
      data.user_id = Number(data.user_id);
      data.semester = Number(data.semester);
      try { await api("/api/admin/mappings", { method: "POST", body: JSON.stringify(data) }); dialog.close(); notify("Subject mapping saved."); await navigate("users"); }
      catch (error) { document.querySelector("#dialog-error").textContent = error.message; }
    });
  } catch (error) { notify(error.message, true); }
}

async function navigate(view) {
  try { await renderDashboard(view); }
  catch (error) { notify(error.message, true); }
}

async function logout() {
  try { await api("/api/auth/logout", { method: "POST", body: "{}" }); }
  finally { state.user = null; state.csrf = null; showLogin(); }
}

async function start() {
  try {
    const result = await api("/api/me");
    state.user = result.user;
    state.csrf = result.csrf_token;
    await renderDashboard();
  } catch { showLogin(); }
}

document.addEventListener("click", event => {
  if (event.target.matches(".notification-button")) navigate("notifications");
  if (event.target.matches(".dialog")) event.target.close();
});
showLogin();
start();
