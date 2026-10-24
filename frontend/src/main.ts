import "./app.css";
import { mount } from "svelte";
import App from "./App.svelte";

import { chatStore } from "./lib/chatStore.svelte";
import { studioStore } from "./lib/studioStore.svelte";

if (typeof window !== "undefined") {
  (window as any).__CHAT_STORE__ = chatStore;
  (window as any).__STUDIO_STORE__ = studioStore;
}

const app = mount(App, {
  target: document.getElementById("app")!,
});

export default app;
