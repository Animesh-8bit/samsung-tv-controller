import Cocoa
import WebKit

class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate, WKScriptMessageHandler, WKNavigationDelegate {
    var window: NSWindow!
    var webView: WKWebView!
    var statusTimer: Timer?

    func applicationDidFinishLaunching(_ notification: Notification) {
        setupMenu()
        setupWindow()
        loadWebInterface()
        startStatusTimer()
    }

    private func setupWindow() {
        let width: CGFloat = 380
        let height: CGFloat = 820
        let rect = NSRect(x: 0, y: 0, width: width, height: height)

        window = NSWindow(
            contentRect: rect,
            styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView],
            backing: .buffered,
            defer: false
        )
        window.center()
        window.title = "Samsung TV Controller"
        window.titlebarAppearsTransparent = true
        window.titleVisibility = .hidden
        window.backgroundColor = NSColor(red: 0.08, green: 0.09, blue: 0.11, alpha: 1.0)
        window.isMovableByWindowBackground = true
        window.minSize = NSSize(width: 320, height: 580)
        window.delegate = self

        let contentController = WKUserContentController()
        contentController.add(self, name: "samsung")

        let config = WKWebViewConfiguration()
        config.userContentController = contentController
        config.preferences.setValue(true, forKey: "developerExtrasEnabled")

        webView = WKWebView(frame: rect, configuration: config)
        webView.navigationDelegate = self
        webView.setValue(false, forKey: "drawsBackground") // Transparent background
        webView.autoresizingMask = [.width, .height]
        window.contentView = webView

        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    private func setupMenu() {
        let mainMenu = NSMenu()
        
        // App Menu
        let appMenuItem = NSMenuItem()
        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "About Samsung TV Controller", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: "")
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(withTitle: "Hide Samsung TV Controller", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h")
        appMenu.addItem(withTitle: "Hide Others", action: #selector(NSApplication.hideOtherApplications(_:)), keyEquivalent: "h")
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(withTitle: "Quit Samsung TV Controller", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appMenuItem.submenu = appMenu
        mainMenu.addItem(appMenuItem)
        
        // Window Menu
        let windowMenuItem = NSMenuItem()
        let windowMenu = NSMenu(title: "Window")
        windowMenu.addItem(withTitle: "Minimize", action: #selector(NSWindow.performMiniaturize(_:)), keyEquivalent: "m")
        windowMenu.addItem(withTitle: "Zoom", action: #selector(NSWindow.performZoom(_:)), keyEquivalent: "")
        windowMenuItem.submenu = windowMenu
        mainMenu.addItem(windowMenuItem)
        
        NSApp.mainMenu = mainMenu
    }

    private func loadWebInterface() {
        if let resourceURL = Bundle.main.resourceURL {
            let webDir = resourceURL.appendingPathComponent("web")
            let htmlFile = webDir.appendingPathComponent("index.html")
            if FileManager.default.fileExists(atPath: htmlFile.path) {
                webView.loadFileURL(htmlFile, allowingReadAccessTo: webDir)
                return
            }
        }
        
        // Fallback for local debugging
        let localPath = "/Users/admin/samsung-tv-controller/frontend/index.html"
        let localDir = URL(fileURLWithPath: "/Users/admin/samsung-tv-controller/frontend")
        let fileURL = URL(fileURLWithPath: localPath)
        if FileManager.default.fileExists(atPath: localPath) {
            webView.loadFileURL(fileURL, allowingReadAccessTo: localDir)
        }
    }

    // MARK: - WKScriptMessageHandler
    
    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard message.name == "samsung",
              let dict = message.body as? [String: Any],
              let action = dict["action"] as? String else {
            return
        }

        switch action {
        case "key":
            if let key = dict["key"] as? String {
                SamsungClient.shared.sendKey(key)
            }
        case "power":
            SamsungClient.shared.powerToggle()
        case "app":
            if let appId = dict["appId"] as? String {
                SamsungClient.shared.launchApp(appId: appId)
            }
        case "browser":
            if let url = dict["url"] as? String {
                SamsungClient.shared.openBrowser(url: url)
            }
        case "text":
            if let text = dict["text"] as? String {
                SamsungClient.shared.sendText(text)
            }
        case "getStatus":
            SamsungClient.shared.fetchStatus { [weak self] status in
                self?.sendJsCallback(function: "updateStatusFromNative", arg: status)
            }
        case "getConfig":
            let config: [String: Any] = [
                "ip": SamsungClient.shared.ip,
                "mac": SamsungClient.shared.mac,
                "port": SamsungClient.shared.port
            ]
            sendJsCallback(function: "updateConfigFromNative", arg: config)
        case "saveConfig":
            if let ip = dict["ip"] as? String, !ip.isEmpty {
                SamsungClient.shared.ip = ip
            }
            if let mac = dict["mac"] as? String {
                SamsungClient.shared.mac = mac
            }
            if let port = dict["port"] as? Int {
                SamsungClient.shared.port = port
            }
            SamsungClient.shared.saveConfig()
            SamsungClient.shared.fetchStatus { [weak self] status in
                self?.sendJsCallback(function: "updateStatusFromNative", arg: status)
            }
        case "discover":
            SamsungClient.shared.discoverTvs { [weak self] tvs in
                self?.sendJsCallback(function: "updateDiscoveryFromNative", arg: tvs)
            }
        default:
            break
        }
    }

    private func sendJsCallback(function: String, arg: Any) {
        guard let data = try? JSONSerialization.data(withJSONObject: arg),
              let jsonStr = String(data: data, encoding: .utf8) else {
            return
        }
        DispatchQueue.main.async {
            self.webView.evaluateJavaScript("\(function)(\(jsonStr))", completionHandler: nil)
        }
    }

    private func startStatusTimer() {
        statusTimer = Timer.scheduledTimer(withTimeInterval: 5.0, repeats: true) { [weak self] _ in
            SamsungClient.shared.fetchStatus { [weak self] status in
                self?.sendJsCallback(function: "updateStatusFromNative", arg: status)
            }
        }
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        // Initial status query
        SamsungClient.shared.fetchStatus { [weak self] status in
            self?.sendJsCallback(function: "updateStatusFromNative", arg: status)
        }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return true
    }
}
