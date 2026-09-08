// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::fs;
use std::path::{Path, PathBuf};
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ActiveGitContext {
    pub organization: String,
    pub repo: String,
    pub branch: String,
    pub task_key: String,
    pub is_git_repo: bool,
    pub detected_path: String,
}

fn find_git_root(start_dir: &Path) -> Option<PathBuf> {
    let mut current = start_dir.to_path_buf();
    loop {
        let git_dir = current.join(".git");
        if git_dir.exists() {
            return Some(current);
        }
        if !current.pop() {
            break;
        }
    }
    None
}

fn extract_task_key(branch: &str) -> String {
    // Looks for patterns like BILL-204, PROJ-101, FEAT-42
    let bytes = branch.as_bytes();
    for i in 0..bytes.len() {
        if bytes[i] == b'-' {
            // Check prefix letters
            let mut start = i;
            while start > 0 && bytes[start - 1].is_ascii_alphabetic() {
                start -= 1;
            }
            // Check suffix digits
            let mut end = i + 1;
            while end < bytes.len() && bytes[end].is_ascii_digit() {
                end += 1;
            }
            if start < i && end > i + 1 {
                let prefix_len = i - start;
                let suffix_len = end - (i + 1);
                if prefix_len >= 2 && suffix_len >= 1 {
                    return branch[start..end].to_uppercase();
                }
            }
        }
    }
    "ACTIVE".to_string()
}

fn parse_remote_origin(config_content: &str) -> Option<(String, String)> {
    // Parses origin URL e.g. git@github.com:snapmeet/billing-service.git
    // or https://github.com/snapmeet/billing-service.git
    let mut in_remote_origin = false;
    for line in config_content.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with('[') && trimmed.ends_with(']') {
            in_remote_origin = trimmed.contains("remote \"origin\"");
        } else if in_remote_origin && trimmed.starts_with("url = ") {
            let raw_url = trimmed.trim_start_matches("url = ").trim();
            // Handle SSH: git@github.com:owner/repo.git
            let path_part = if let Some(idx) = raw_url.find(':') {
                &raw_url[idx + 1..]
            } else if let Some(idx) = raw_url.find("github.com/") {
                &raw_url[idx + 11..]
            } else if let Some(idx) = raw_url.find("gitlab.com/") {
                &raw_url[idx + 11..]
            } else {
                raw_url
            };
            let clean = path_part.trim_end_matches(".git").trim_start_matches('/');
            let segments: Vec<&str> = clean.split('/').collect();
            if segments.len() >= 2 {
                return Some((segments[0].to_string(), segments[1].to_string()));
            }
        }
    }
    None
}

pub fn detect_git_context(custom_path: Option<&str>) -> ActiveGitContext {
    let start_dir = match custom_path {
        Some(p) => PathBuf::from(p),
        None => std::env::current_dir().unwrap_or_else(|_| PathBuf::from(".")),
    };

    if let Some(git_root) = find_git_root(&start_dir) {
        let git_dir = git_root.join(".git");
        let head_file = git_dir.join("HEAD");
        let config_file = git_dir.join("config");

        let mut branch = "main".to_string();
        if let Ok(head_content) = fs::read_to_string(&head_file) {
            let trimmed = head_content.trim();
            if let Some(ref_path) = trimmed.strip_prefix("ref: refs/heads/") {
                branch = ref_path.to_string();
            } else if trimmed.len() >= 7 {
                branch = trimmed[..7].to_string();
            }
        }

        let mut org = "snapmeet".to_string();
        let mut repo = git_root
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("repository")
            .to_string();

        if let Ok(cfg_content) = fs::read_to_string(&config_file) {
            if let Some((parsed_org, parsed_repo)) = parse_remote_origin(&cfg_content) {
                org = parsed_org;
                repo = parsed_repo;
            }
        }

        let task_key = extract_task_key(&branch);

        ActiveGitContext {
            organization: org,
            repo,
            branch,
            task_key,
            is_git_repo: true,
            detected_path: git_root.to_string_lossy().to_string(),
        }
    } else {
        // Safe fallback default
        ActiveGitContext {
            organization: "snapmeet".to_string(),
            repo: "billing-service".to_string(),
            branch: "feat/BILL-204-razorpay-retry".to_string(),
            task_key: "BILL-204".to_string(),
            is_git_repo: false,
            detected_path: start_dir.to_string_lossy().to_string(),
        }
    }
}

use tauri::{Manager, Emitter};

#[tauri::command]
fn get_active_context(custom_path: Option<String>) -> ActiveGitContext {
    detect_git_context(custom_path.as_deref())
}

#[tauri::command]
fn set_hud_window_size(app_handle: tauri::AppHandle, width: f64, height: f64) {
    if let Some(window) = app_handle.get_webview_window("kairo-hud") {
        #[cfg(target_os = "windows")]
        {
            extern "system" {
                fn SetWindowPos(
                    hWnd: *mut std::ffi::c_void,
                    hWndInsertAfter: *mut std::ffi::c_void,
                    X: i32,
                    Y: i32,
                    cx: i32,
                    cy: i32,
                    uFlags: u32,
                ) -> i32;
            }
            if let Ok(hwnd) = window.hwnd() {
                // SWP_NOMOVE (0x0002) | SWP_NOZORDER (0x0004) | SWP_NOACTIVATE (0x0010)
                unsafe {
                    SetWindowPos(
                        hwnd.0 as *mut std::ffi::c_void,
                        std::ptr::null_mut(),
                        0,
                        0,
                        width as i32,
                        height as i32,
                        0x0002 | 0x0004 | 0x0010,
                    );
                }
            }
        }
        let _ = window.set_size(tauri::LogicalSize::new(width, height));
    }
}

#[tauri::command]
fn show_hud(app_handle: tauri::AppHandle) {
    if let Some(window) = app_handle.get_webview_window("kairo-hud") {
        set_hud_window_size(app_handle.clone(), 200.0, 54.0);
        let _ = window.show();
        let _ = window.set_focus();
        let _ = app_handle.emit("wake-hud-icon", ());
    }
}

#[tauri::command]
fn hide_hud(app_handle: tauri::AppHandle) {
    if let Some(window) = app_handle.get_webview_window("kairo-hud") {
        set_hud_window_size(app_handle.clone(), 200.0, 54.0);
        let _ = window.hide();
        let _ = app_handle.emit("deactivate-hud", ());
    }
}

#[tauri::command]
fn toggle_hud(app_handle: tauri::AppHandle) {
    if let Some(window) = app_handle.get_webview_window("kairo-hud") {
        let is_vis = window.is_visible().unwrap_or(false);
        if is_vis {
            set_hud_window_size(app_handle.clone(), 200.0, 54.0);
            let _ = window.hide();
            let _ = app_handle.emit("deactivate-hud", ());
        } else {
            set_hud_window_size(app_handle.clone(), 200.0, 54.0);
            let _ = window.show();
            let _ = window.set_focus();
            let _ = app_handle.emit("wake-hud-icon", ());
        }
    }
}

#[cfg(target_os = "windows")]
static GLOBAL_APP_HANDLE: std::sync::OnceLock<tauri::AppHandle> = std::sync::OnceLock::new();

#[cfg(target_os = "windows")]
#[derive(Clone, Copy)]
#[repr(C)]
struct KbdllHookStruct {
    vk_code: u32,
    scan_code: u32,
    flags: u32,
    time: u32,
    extra_info: usize,
}

#[cfg(target_os = "windows")]
unsafe extern "system" fn low_level_keyboard_proc(
    n_code: i32,
    w_param: usize,
    l_param: isize,
) -> isize {
    extern "system" {
        fn CallNextHookEx(
            hhk: *mut std::ffi::c_void,
            nCode: i32,
            wParam: usize,
            lParam: isize,
        ) -> isize;
        fn GetAsyncKeyState(vKey: i32) -> i16;
    }

    if n_code >= 0 && (w_param == 0x0100 || w_param == 0x0104) {
        let kb = *(l_param as *const KbdllHookStruct);
        // VK_CONTROL = 0x11
        let ctrl_down = (GetAsyncKeyState(0x11) as u16 & 0x8000) != 0;

        // 1. Ctrl + Space: Wake up chota wala HUD (or hide if already shown)
        if kb.vk_code == 0x20 && ctrl_down {
            if let Some(app_handle) = GLOBAL_APP_HANDLE.get() {
                if let Some(window) = app_handle.get_webview_window("kairo-hud") {
                    let is_vis = window.is_visible().unwrap_or(false);
                    if is_vis {
                        set_hud_window_size(app_handle.clone(), 200.0, 54.0);
                        let _ = window.hide();
                        let _ = app_handle.emit("deactivate-hud", ());
                    } else {
                        // Open chota wala HUD (200x54) on wake
                        set_hud_window_size(app_handle.clone(), 200.0, 54.0);
                        let _ = window.show();
                        let _ = window.set_focus();
                        let _ = app_handle.emit("wake-hud-icon", ());
                    }
                }
            }
            return 1; // Consume key so VS Code / IME doesn't catch it
        }

        // 2. Escape: Deactivate / hide HUD without logging out
        if kb.vk_code == 0x1B {
            if let Some(app_handle) = GLOBAL_APP_HANDLE.get() {
                if let Some(window) = app_handle.get_webview_window("kairo-hud") {
                    if window.is_visible().unwrap_or(false) {
                        set_hud_window_size(app_handle.clone(), 200.0, 54.0);
                        let _ = window.hide();
                        let _ = app_handle.emit("deactivate-hud", ());
                        return 1; // Consume key
                    }
                }
            }
        }
    }

    CallNextHookEx(std::ptr::null_mut(), n_code, w_param, l_param)
}

#[repr(C)]
struct Win32Point {
    x: i32,
    y: i32,
}

#[repr(C)]
struct Win32Msg {
    hwnd: *mut std::ffi::c_void,
    message: u32,
    wparam: usize,
    lparam: isize,
    time: u32,
    pt: Win32Point,
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            #[cfg(target_os = "windows")]
            {
                let _ = GLOBAL_APP_HANDLE.set(app.handle().clone());
                std::thread::spawn(move || {
                    unsafe {
                        extern "system" {
                            fn SetWindowsHookExW(
                                idHook: i32,
                                lpfn: unsafe extern "system" fn(i32, usize, isize) -> isize,
                                hmod: *mut std::ffi::c_void,
                                dwThreadId: u32,
                            ) -> *mut std::ffi::c_void;
                            fn GetMessageW(
                                lpMsg: *mut std::ffi::c_void,
                                hWnd: *mut std::ffi::c_void,
                                wMsgFilterMin: u32,
                                wMsgFilterMax: u32,
                            ) -> i32;
                            fn UnhookWindowsHookEx(hhk: *mut std::ffi::c_void) -> i32;
                        }

                        // 13 = WH_KEYBOARD_LL
                        let hook = SetWindowsHookExW(13, low_level_keyboard_proc, std::ptr::null_mut(), 0);
                        if !hook.is_null() {
                            let mut msg = std::mem::zeroed::<Win32Msg>();
                            while GetMessageW(
                                &mut msg as *mut _ as *mut std::ffi::c_void,
                                std::ptr::null_mut(),
                                0,
                                0,
                            ) > 0
                            {}
                            UnhookWindowsHookEx(hook);
                        }
                    }
                });
            }

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_active_context,
            set_hud_window_size,
            show_hud,
            hide_hud,
            toggle_hud
        ])
        .run(tauri::generate_context!())
        .expect("error while running KAIRO HUD application");
}
