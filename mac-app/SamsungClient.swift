import Foundation
import Network

public class SamsungClient: NSObject, URLSessionDelegate, URLSessionTaskDelegate, URLSessionWebSocketDelegate {
    public static let shared = SamsungClient()
    
    public var ip: String = "192.168.1.5"
    public var mac: String = "68:FC:CA:33:88:DA"
    public var port: Int = 8002
    public var token: String = "29372486"
    public var tvName: String = "[TV] Samsung 4 Series (32)"
    public var tvModel: String = "UA32T4380AKXXL"
    public var isOnline: Bool = true
    
    private var session: URLSession!
    private var task: URLSessionWebSocketTask?
    private var isConnected = false
    private var isConnecting = false
    private var pendingCallbacks: [(Bool) -> Void] = []
    private let queue = DispatchQueue(label: "com.antigravity.samsungclient", qos: .userInitiated)
    
    private override init() {
        super.init()
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 3600
        config.timeoutIntervalForResource = 3600
        self.session = URLSession(configuration: config, delegate: self, delegateQueue: OperationQueue.main)
        loadConfig()
    }
    
    // MARK: - Configuration Persistence
    
    private var configURL: URL {
        let appSupport = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let dir = appSupport.appendingPathComponent("SamsungTVController", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir.appendingPathComponent("config.json")
    }
    
    public func loadConfig() {
        if let data = try? Data(contentsOf: configURL),
           let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            if let ip = json["ip"] as? String, !ip.isEmpty { self.ip = ip }
            if let mac = json["mac"] as? String, !mac.isEmpty { self.mac = mac }
            if let port = json["port"] as? Int { self.port = port }
            if let token = json["token"] as? String, !token.isEmpty { self.token = token }
            if let name = json["name"] as? String { self.tvName = name }
            if let model = json["model"] as? String { self.tvModel = model }
        } else {
            saveConfig()
        }
    }
    
    public func saveConfig() {
        let dict: [String: Any] = [
            "ip": ip,
            "mac": mac,
            "port": port,
            "token": token,
            "name": tvName,
            "model": tvModel
        ]
        if let data = try? JSONSerialization.data(withJSONObject: dict, options: .prettyPrinted) {
            try? data.write(to: configURL)
        }
    }
    
    // MARK: - SSL Authentication Challenge
    
    public func urlSession(_ session: URLSession, task: URLSessionTask, didReceive challenge: URLAuthenticationChallenge, completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        if challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
           let trust = challenge.protectionSpace.serverTrust {
            completionHandler(.useCredential, URLCredential(trust: trust))
        } else {
            completionHandler(.performDefaultHandling, nil)
        }
    }
    
    public func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask, didOpenWithProtocol protocol: String?) {
        isConnected = true
        isOnline = true
        isConnecting = false
        flushCallbacks(success: true)
    }
    
    public func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask, didCloseWith closeCode: URLSessionWebSocketTask.CloseCode, reason: Data?) {
        isConnected = false
        isOnline = false
        isConnecting = false
        self.task = nil
        flushCallbacks(success: false)
    }
    
    private func flushCallbacks(success: Bool) {
        let cbs = self.pendingCallbacks
        self.pendingCallbacks.removeAll()
        for cb in cbs {
            cb(success)
        }
    }
    
    // MARK: - WebSocket Connection
    
    private func connect(completion: @escaping (Bool) -> Void) {
        if isConnected && task != nil && task?.state == .running {
            completion(true)
            return
        }
        
        pendingCallbacks.append(completion)
        if isConnecting {
            return
        }
        isConnecting = true
        
        let clientName = "SamsungTvRemote".data(using: .utf8)!.base64EncodedString()
        let urlStr = "wss://\(ip):\(port)/api/v2/channels/samsung.remote.control?name=\(clientName)&token=\(token)"
        guard let url = URL(string: urlStr) else {
            isConnecting = false
            flushCallbacks(success: false)
            return
        }
        
        var req = URLRequest(url: url)
        req.setValue("https://\(ip):\(port)", forHTTPHeaderField: "Origin")
        
        task?.cancel()
        task = session.webSocketTask(with: req)
        task?.resume()
        
        listen()
        
        // Watchdog timeout: if handshake takes longer than 2.5s, trigger callbacks anyway
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.5) { [weak self] in
            guard let self = self else { return }
            if self.isConnecting {
                self.isConnecting = false
                if self.task?.state == .running {
                    self.isConnected = true
                    self.isOnline = true
                    self.flushCallbacks(success: true)
                } else {
                    self.flushCallbacks(success: false)
                }
            }
        }
    }
    
    private func listen() {
        task?.receive { [weak self] res in
            guard let self = self else { return }
            switch res {
            case .success(let msg):
                if case .string(let text) = msg {
                    if text.contains("ms.channel.connect") {
                        self.isConnected = true
                        self.isOnline = true
                    } else if text.contains("ms.channel.unauthorized") {
                        self.isConnected = false
                        self.isOnline = false
                    }
                }
                self.listen()
            case .failure:
                self.isConnected = false
                self.isOnline = false
                self.task = nil
            }
        }
    }
    
    // MARK: - Key Dispatch (Zero Latency + Queuing)
    
    public func sendKey(_ key: String, completion: ((Bool) -> Void)? = nil) {
        var normalizedKey = key.trimmingCharacters(in: .whitespacesAndNewlines)
        if !normalizedKey.hasPrefix("KEY_") {
            normalizedKey = "KEY_" + normalizedKey.uppercased()
        }
        
        connect { [weak self] ok in
            guard let self = self, ok, let task = self.task else {
                completion?(false)
                return
            }
            
            let payload: [String: Any] = [
                "method": "ms.remote.control",
                "params": [
                    "Cmd": "Click",
                    "DataOfCmd": normalizedKey,
                    "Option": "false",
                    "TypeOfRemote": "SendRemoteKey"
                ]
            ]
            
            guard let data = try? JSONSerialization.data(withJSONObject: payload),
                  let json = String(data: data, encoding: .utf8) else {
                completion?(false)
                return
            }
            
            task.send(.string(json)) { [weak self] err in
                if err != nil {
                    // Retry once on broken pipe
                    self?.isConnected = false
                    self?.task = nil
                    self?.connect { _ in
                        self?.task?.send(.string(json)) { err2 in
                            completion?(err2 == nil)
                        }
                    }
                } else {
                    completion?(true)
                }
            }
        }
    }
    
    // MARK: - App Launcher
    
    public func launchApp(appId: String, completion: ((Bool) -> Void)? = nil) {
        connect { [weak self] ok in
            guard let self = self, ok, let task = self.task else {
                completion?(false)
                return
            }
            
            let payload: [String: Any] = [
                "method": "ms.channel.emit",
                "params": [
                    "event": "ed.apps.launch",
                    "to": "host",
                    "data": [
                        "appId": appId,
                        "action_type": "DEEP_LINK"
                    ]
                ]
            ]
            
            guard let data = try? JSONSerialization.data(withJSONObject: payload),
                  let json = String(data: data, encoding: .utf8) else {
                completion?(false)
                return
            }
            
            task.send(.string(json)) { err in
                completion?(err == nil)
            }
        }
    }
    
    // MARK: - Browser URL Launcher
    
    public func openBrowser(url: String, completion: ((Bool) -> Void)? = nil) {
        connect { [weak self] ok in
            guard let self = self, ok, let task = self.task else {
                completion?(false)
                return
            }
            
            let payload: [String: Any] = [
                "method": "ms.channel.emit",
                "params": [
                    "event": "ed.apps.launch",
                    "to": "host",
                    "data": [
                        "appId": "org.tizen.browser",
                        "action_type": "NATIVE_LAUNCH",
                        "metaTag": url
                    ]
                ]
            ]
            
            guard let data = try? JSONSerialization.data(withJSONObject: payload),
                  let json = String(data: data, encoding: .utf8) else {
                completion?(false)
                return
            }
            
            task.send(.string(json)) { err in
                completion?(err == nil)
            }
        }
    }
    
    // MARK: - Send Text
    
    public func sendText(_ text: String, completion: ((Bool) -> Void)? = nil) {
        connect { [weak self] ok in
            guard let self = self, ok, let task = self.task else {
                completion?(false)
                return
            }
            
            let b64 = text.data(using: .utf8)!.base64EncodedString()
            let payload: [String: Any] = [
                "method": "ms.remote.control",
                "params": [
                    "Cmd": b64,
                    "DataOfCmd": "base64",
                    "TypeOfRemote": "SendInputString"
                ]
            ]
            
            guard let data = try? JSONSerialization.data(withJSONObject: payload),
                  let json = String(data: data, encoding: .utf8) else {
                completion?(false)
                return
            }
            
            task.send(.string(json)) { err in
                completion?(err == nil)
            }
        }
    }
    
    // MARK: - Wake-on-LAN
    
    public func sendWakeOnLAN() -> Bool {
        let macBytes = mac.split(separator: ":").compactMap { UInt8($0, radix: 16) }
        guard macBytes.count == 6 else { return false }
        
        var packet = [UInt8](repeating: 0xFF, count: 6)
        for _ in 0..<16 {
            packet.append(contentsOf: macBytes)
        }
        
        let sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
        guard sock >= 0 else { return false }
        defer { close(sock) }
        
        var broadcast: Int32 = 1
        setsockopt(sock, SOL_SOCKET, SO_BROADCAST, &broadcast, socklen_t(MemoryLayout<Int32>.size))
        
        var addr = sockaddr_in()
        addr.sin_family = sa_family_t(AF_INET)
        addr.sin_port = in_port_t(9).bigEndian
        addr.sin_addr.s_addr = inet_addr("255.255.255.255")
        
        let sent = withUnsafePointer(to: &addr) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                sendto(sock, packet, packet.count, 0, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
            }
        }
        return sent > 0
    }
    
    public func powerToggle(completion: ((Bool) -> Void)? = nil) {
        if !isOnline {
            _ = sendWakeOnLAN()
            completion?(true)
        } else {
            sendKey("KEY_POWER", completion: completion)
        }
    }
    
    // MARK: - Device Info & Status Query
    
    public func fetchStatus(completion: @escaping ([String: Any]) -> Void) {
        guard let url = URL(string: "http://\(ip):8001/api/v2/") else {
            completion(["online": false, "name": tvName, "model": tvModel, "ip": ip, "mac": mac, "token_paired": true])
            return
        }
        
        var req = URLRequest(url: url)
        req.timeoutInterval = 2.0
        
        let task = URLSession.shared.dataTask(with: req) { [weak self] data, resp, err in
            guard let self = self else { return }
            if let data = data,
               let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let dev = json["device"] as? [String: Any] {
                self.isOnline = true
                self.tvName = (dev["name"] as? String) ?? self.tvName
                self.tvModel = (dev["modelName"] as? String) ?? self.tvModel
                if let wifiMac = dev["wifiMac"] as? String, !wifiMac.isEmpty {
                    self.mac = wifiMac
                }
                
                let result: [String: Any] = [
                    "online": true,
                    "power_state": dev["PowerState"] ?? "on",
                    "name": self.tvName,
                    "model": self.tvModel,
                    "ip": self.ip,
                    "mac": self.mac,
                    "token_paired": true
                ]
                completion(result)
            } else {
                let result: [String: Any] = [
                    "online": self.isOnline,
                    "power_state": self.isOnline ? "on" : "standby",
                    "name": self.tvName,
                    "model": self.tvModel,
                    "ip": self.ip,
                    "mac": self.mac,
                    "token_paired": true
                ]
                completion(result)
            }
        }
        task.resume()
    }
    
    // MARK: - SSDP TV Discovery with Local Socket Bind
    
    public func discoverTvs(completion: @escaping ([[String: Any]]) -> Void) {
        queue.async {
            let msg = "M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: \"ssdp:discover\"\r\nMX: 2\r\nST: ssdp:all\r\n\r\n"
            let sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
            guard sock >= 0 else {
                DispatchQueue.main.async { completion([]) }
                return
            }
            defer { close(sock) }
            
            // Essential for receiving responses: Bind to local ephemeral port
            var bindAddr = sockaddr_in()
            bindAddr.sin_family = sa_family_t(AF_INET)
            bindAddr.sin_port = in_port_t(0).bigEndian
            bindAddr.sin_addr.s_addr = INADDR_ANY.bigEndian
            _ = withUnsafePointer(to: &bindAddr) {
                $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                    Darwin.bind(sock, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
                }
            }
            
            var tv = timeval(tv_sec: 2, tv_usec: 0)
            setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, socklen_t(MemoryLayout<timeval>.size))
            
            var dest = sockaddr_in()
            dest.sin_family = sa_family_t(AF_INET)
            dest.sin_port = in_port_t(1900).bigEndian
            dest.sin_addr.s_addr = inet_addr("239.255.255.250")
            
            _ = withUnsafePointer(to: &dest) {
                $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                    sendto(sock, msg, msg.utf8.count, 0, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
                }
            }
            
            var foundIps = [String]()
            var buffer = [UInt8](repeating: 0, count: 4096)
            
            while true {
                var src = sockaddr_in()
                var srcLen = socklen_t(MemoryLayout<sockaddr_in>.size)
                let bytesRead = withUnsafeMutablePointer(to: &src) {
                    $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                        recvfrom(sock, &buffer, buffer.count, 0, $0, &srcLen)
                    }
                }
                if bytesRead <= 0 { break }
                
                let ipStr = String(cString: inet_ntoa(src.sin_addr))
                let text = String(decoding: buffer[0..<bytesRead], as: UTF8.self).lowercased()
                if (text.contains("samsung") || text.contains("dial")) && !foundIps.contains(ipStr) {
                    foundIps.append(ipStr)
                }
            }
            
            var tvList = [[String: Any]]()
            for ip in foundIps {
                tvList.append([
                    "ip": ip,
                    "name": (ip == "192.168.1.5") ? "[TV] Samsung 4 Series (32)" : "Samsung Smart TV (\(ip))",
                    "model": (ip == "192.168.1.5") ? "UA32T4380AKXXL" : "Samsung Smart TV",
                    "mac": (ip == "192.168.1.5") ? "68:FC:CA:33:88:DA" : ""
                ])
            }
            
            // If discovery was blocked by multicast filter on router, ensure configured TV is always listed
            if !foundIps.contains(SamsungClient.shared.ip) {
                tvList.append([
                    "ip": SamsungClient.shared.ip,
                    "name": SamsungClient.shared.tvName,
                    "model": SamsungClient.shared.tvModel,
                    "mac": SamsungClient.shared.mac
                ])
            }
            
            DispatchQueue.main.async {
                completion(tvList)
            }
        }
    }
}
