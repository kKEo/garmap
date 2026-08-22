<!--
  A framed terminal window for shell transcripts.

  Every transcript in this deck is real output captured from a working machine,
  so the frame is a promise: what you see is what you get.

  The slot must contain a fenced code block, not bare lines:

    <Terminal title="garmap doctor">

    ```text
    OK    runtime    openjdk version "21.0.6"
    ```

    </Terminal>

  Bare lines are markdown, and markdown collapses them into one paragraph --
  every newline and every run of indentation in the transcript is lost, which is
  exactly what this frame promises not to happen.  A fenced block reaches the
  component as a shiki <pre> with its line structure intact; the styles below
  strip shiki's own light background and let the frame's dark one show through.
-->
<template>
  <div class="term">
    <div class="term-bar">
      <span class="dot dot-red" />
      <span class="dot dot-amber" />
      <span class="dot dot-green" />
      <span class="term-title">{{ title }}</span>
    </div>
    <div class="term-body"><slot /></div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: 'zsh' },
})
</script>

<style scoped>
.term {
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.28);
  background: #12161c;
  font-size: 0.8em;
}
.term-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 10px;
  background: #232a33;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}
.dot-red { background: #ff5f57; }
.dot-amber { background: #febc2e; }
.dot-green { background: #28c840; }
.term-title {
  margin-left: 8px;
  color: #8b98a8;
  font-family: ui-monospace, SFMono-Regular, monospace;
  font-size: 0.85em;
}
.term-body {
  padding: 12px 14px;
  color: #d7dee8;
  background: #12161c;
  line-height: 1.45;
}
/* Shiki brings its own <pre>, background and padding; the frame supplies all
   three, so flatten it and keep only the preserved line structure. */
.term-body :deep(pre) {
  margin: 0;
  padding: 0;
  background: transparent !important;
  font-family: ui-monospace, SFMono-Regular, monospace;
  white-space: pre;
  overflow-x: auto;
}
.term-body :deep(code),
.term-body :deep(.line span) {
  color: #d7dee8 !important;
}
</style>
