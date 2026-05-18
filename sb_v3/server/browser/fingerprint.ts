/**
 * Browser fingerprint generator.
 * Generates randomized profiles to defeat anti-bot fingerprinting systems.
 * Ported from legacy Python credit_score_bot.
 */

import { randomInt } from "crypto";

interface FingerprintProfile {
  userAgent: string;
  screenWidth: number;
  screenHeight: number;
  timezone: string;
  languages: string[];
  platform: string;
  hardwareConcurrency: number;
  deviceMemory: number;
  webglVendor: string;
  webglRenderer: string;
  canvasNoiseSeed: number;
  audioNoiseSeed: number;
  doNotTrack: string | null;
}

const SCREEN_RESOLUTIONS: [number, number][] = [
  [1366, 768], [1920, 1080], [1440, 900], [1536, 864],
  [1280, 800], [1600, 900], [1280, 1024], [1024, 768],
  [1680, 1050], [1920, 1200], [2560, 1440], [1360, 768],
];

const TIMEZONES = [
  "America/New_York", "America/Chicago", "America/Denver",
  "America/Los_Angeles", "America/Phoenix", "America/Detroit",
  "America/Indiana/Indianapolis", "America/Boise",
  "America/Anchorage", "Pacific/Honolulu",
];

const LANGUAGES: string[][] = [
  ["en-US", "en"],
  ["en-US", "en", "es"],
  ["en-US", "en-GB", "en"],
  ["en-US"],
];

const PLATFORMS = ["Win32", "Win32", "Win32", "MacIntel", "Linux x86_64"];
const CPU_CORES = [2, 4, 4, 4, 6, 8, 8, 12, 16];
const DEVICE_MEMORY = [2, 4, 4, 8, 8, 16];

const WEBGL_VENDORS: [string, string][] = [
  ["Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1060 6GB Direct3D11 vs_5_0 ps_5_0, D3D11)"],
  ["Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11)"],
  ["Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0, D3D11)"],
  ["Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 2060 Direct3D11 vs_5_0 ps_5_0, D3D11)"],
  ["Intel Inc.", "Intel Iris OpenGL Engine"],
  ["Apple Inc.", "Apple GPU"],
];

const FF_VERSIONS = ["115.0", "116.0", "117.0", "118.0", "119.0", "120.0", "121.0", "122.0", "123.0"];
const WIN_VERSIONS = [
  "Windows NT 10.0; Win64; x64",
  "Windows NT 10.0; WOW64",
  "Windows NT 6.1; Win64; x64",
];
const MAC_VERSIONS = [
  "Macintosh; Intel Mac OS X 10.15",
  "Macintosh; Intel Mac OS X 11.0",
  "Macintosh; Intel Mac OS X 12.0",
  "Macintosh; Intel Mac OS X 13.0",
];

function pick<T>(arr: T[]): T {
  return arr[randomInt(arr.length)];
}

export function generateFingerprint(): FingerprintProfile {
  const screen = pick(SCREEN_RESOLUTIONS);
  const tz = pick(TIMEZONES);
  const langs = pick(LANGUAGES);
  const platform = pick(PLATFORMS);
  const cores = pick(CPU_CORES);
  const mem = pick(DEVICE_MEMORY);
  const webgl = pick(WEBGL_VENDORS);
  const ffVer = pick(FF_VERSIONS);

  let osStr: string;
  if (platform === "MacIntel") {
    osStr = pick(MAC_VERSIONS);
  } else if (platform === "Linux x86_64") {
    osStr = "X11; Linux x86_64";
  } else {
    osStr = pick(WIN_VERSIONS);
  }

  const userAgent = `Mozilla/5.0 (${osStr}; rv:${ffVer}) Gecko/20100101 Firefox/${ffVer}`;

  return {
    userAgent,
    screenWidth: screen[0],
    screenHeight: screen[1],
    timezone: tz,
    languages: langs,
    platform,
    hardwareConcurrency: cores,
    deviceMemory: mem,
    webglVendor: webgl[0],
    webglRenderer: webgl[1],
    canvasNoiseSeed: randomInt(1, 999999),
    audioNoiseSeed: randomInt(1, 999999),
    doNotTrack: Math.random() > 0.33 ? "1" : null,
  };
}

export function toPlaywrightContextOptions(fp: FingerprintProfile) {
  return {
    userAgent: fp.userAgent,
    viewport: { width: fp.screenWidth, height: fp.screenHeight },
    locale: fp.languages[0] ?? "en-US",
    timezoneId: fp.timezone,
    extraHTTPHeaders: {
      "Accept-Language": fp.languages.join(",") + ";q=0.9",
      "DNT": fp.doNotTrack ?? "1",
    },
    deviceScaleFactor: pick([1, 1.5, 2, 3]),
    isMobile: false,
    hasTouch: false,
  };
}

export function getAntiDetectInitScript(): string {
  return `(function() {
    var canvasNoiseSeed = Math.floor(Math.random() * 999998) + 1;
    var audioNoiseSeed = Math.floor(Math.random() * 999998) + 1;

    // Canvas noise — XOR pixel values with random 0-2
    var _origToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type) {
      try {
        var ctx = this.getContext('2d');
        if (ctx) {
          var imageData = ctx.getImageData(0, 0, this.width, this.height);
          var data = imageData.data;
          for (var i = 0; i < data.length; i += 4) {
            data[i]     = data[i]     ^ (Math.random() * 3 | 0);
            data[i + 1] = data[i + 1] ^ (Math.random() * 3 | 0);
            data[i + 2] = data[i + 2] ^ (Math.random() * 3 | 0);
          }
          ctx.putImageData(imageData, 0, 0);
        }
      } catch(e) {}
      return _origToDataURL.apply(this, arguments);
    };

    // Also hook getImageData for canvas-based fingerprinting
    var _origGetImageData = CanvasRenderingContext2D.prototype.getImageData;
    if (_origGetImageData) {
      CanvasRenderingContext2D.prototype.getImageData = function(sx, sy, sw, sh) {
        var imgData = _origGetImageData.call(this, sx, sy, sw, sh);
        try {
          for (var i = 0; i < imgData.data.length; i += 4) {
            imgData.data[i]     = imgData.data[i]     ^ (Math.random() * 3 | 0);
            imgData.data[i + 1] = imgData.data[i + 1] ^ (Math.random() * 3 | 0);
            imgData.data[i + 2] = imgData.data[i + 2] ^ (Math.random() * 3 | 0);
          }
        } catch(e) {}
        return imgData;
      };
    }

    // AudioContext noise
    try {
      var _origGetChanData = AudioBuffer.prototype.getChannelData;
      if (_origGetChanData) {
        AudioBuffer.prototype.getChannelData = function(channel) {
          var data = _origGetChanData.call(this, channel);
          for (var i = 0; i < data.length; i += 100) {
            data[i] += Math.random() * 0.0001 - 0.00005;
          }
          return data;
        };
      }
    } catch(e) {}

    // WebGL noise
    try {
      var _origReadPixels = WebGLRenderingContext.prototype.readPixels;
      if (_origReadPixels) {
        WebGLRenderingContext.prototype.readPixels = function(x, y, w, h, format, type, pixels) {
          _origReadPixels.apply(this, arguments);
          if (pixels && pixels.buffer) {
            var view = new Uint8Array(pixels.buffer);
            for (var i = 0; i < view.length; i += 4) {
              view[i]   ^= Math.random() * 2 | 0;
              view[i+1] ^= Math.random() * 2 | 0;
              view[i+2] ^= Math.random() * 2 | 0;
            }
          }
        };
      }
    } catch(e) {}

    // Battery API — fake data
    if (navigator.getBattery) {
      navigator.getBattery = function() {
        return Promise.resolve({
          charging: true,
          chargingTime: 0,
          dischargingTime: Infinity,
          level: 0.85 + Math.random() * 0.1,
          addEventListener: function() {},
          removeEventListener: function() {},
        });
      };
    }

    // Permissions — return 'prompt' to avoid fingerprinting
    if (navigator.permissions) {
      var _origQuery = navigator.permissions.query.bind(navigator.permissions);
      navigator.permissions.query = function(params) {
        if (['notifications', 'push', 'midi', 'camera', 'microphone'].indexOf(params.name) !== -1) {
          return Promise.resolve({ state: 'prompt', onchange: null });
        }
        return _origQuery(params);
      };
    }

    // Remove automation indicators
    Object.defineProperty(navigator, 'webdriver', { get: function() { return false; } });
    delete navigator.__webdriver_evaluate;

    // Override plugins to look non-bot
    Object.defineProperty(navigator, 'plugins', {
      get: function() {
        return [
          { name: 'PDF Viewer', description: 'Portable Document Format', filename: 'internal-pdf-viewer' },
          { name: 'Chrome PDF Plugin', description: 'Portable Document Format', filename: 'internal-nacl-plugin' },
        ];
      }
    });

    // Override languages
    var _origLang = Object.getOwnPropertyDescriptor(Navigator.prototype, 'language');
    Object.defineProperty(navigator, 'language', {
      get: function() { return 'en-US'; },
      configurable: true
    });
  })();`;
}

export type { FingerprintProfile };