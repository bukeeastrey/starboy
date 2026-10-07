// Records a voice note with the browser's MediaRecorder.

// Android Chrome records webm/opus; iPhones record mp4. Take the first that works.
const FORMATS = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];

export function canRecord() {
  return Boolean(navigator.mediaDevices?.getUserMedia && window.MediaRecorder);
}

// Ask for the microphone and start recording.
// Returns { stop }, where stop() gives back the finished audio (a Blob).
export async function startRecording() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const mimeType = FORMATS.find((format) => MediaRecorder.isTypeSupported(format));
  const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);

  const chunks = [];
  recorder.ondataavailable = (event) => chunks.push(event.data);
  recorder.start();

  function stop() {
    return new Promise((resolve) => {
      recorder.onstop = () => {
        // Switch the microphone off (the red dot in the browser tab goes away).
        stream.getTracks().forEach((track) => track.stop());
        resolve(new Blob(chunks, { type: recorder.mimeType }));
      };
      recorder.stop();
    });
  }

  return { stop };
}
