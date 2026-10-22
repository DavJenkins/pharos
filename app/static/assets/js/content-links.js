"use strict";
const library = new URL(location.href);
library.protocol = "http:";
library.port = "8080";
library.pathname = "/";
library.search = "";
library.hash = "";
document.querySelectorAll("[data-kiwix]").forEach(link => link.href = library.href);
const windows = document.getElementById("windows-share");
const mac = document.getElementById("mac-share");
if (windows) windows.textContent = "\\\\" + location.hostname + "\\Offline-Archives";
if (mac) mac.textContent = "smb://" + location.hostname + "/Offline-Archives";

document.querySelectorAll("[data-ark-host]").forEach(node=>node.textContent=location.hostname);
