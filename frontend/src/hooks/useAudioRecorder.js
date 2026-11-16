/**
 * Custom React Hook for Browser Audio Recording
 *
 * Uses navigator.mediaDevices.getUserMedia and MediaRecorder API.
 * Provides states for isRecording, audioBlob, and recordingDuration,
 * and handles proper stream release to avoid memory leaks.
 * 
 */

import { useState, useRef, useEffect, useCallback } from 'react';

export function useAudioRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [error, setError] = useState(null);

  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerIntervalRef = useRef(null);

  // Check if browser supports audio recording APIs
  const isSupported =
    typeof navigator !== 'undefined' &&
    !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia) &&
    typeof MediaRecorder !== 'undefined';

  /**
   * Release microphone stream tracks and stop recording hardware.
   */
  const releaseMediaStream = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch (err) {
          console.warn('Error stopping media track:', err);
        }
      });
      streamRef.current = null;
    }
  }, []);

  /**
   * Stop timer interval
   */
  const stopTimer = useCallback(() => {
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
  }, []);

  /**
   * Start microphone audio recording.
   */
  const startRecording = useCallback(async () => {
    if (!isSupported) {
      const msg = 'Audio recording is not supported in this browser environment.';
      setError(msg);
      throw new Error(msg);
    }

    // Reset previous recording states
    setError(null);
    setAudioBlob(null);
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
      setAudioUrl(null);
    }
    setRecordingDuration(0);
    audioChunksRef.current = [];

    try {
      // Acoustic machine recording prefers raw audio without aggressive speech DSP
      let stream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: false,
            noiseSuppression: false,
            autoGainControl: false,
          },
        });
      } catch (e) {
        // Fallback to default audio constraints
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      }

      streamRef.current = stream;

      // Select optimal supported MIME type
      const mimeTypes = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/mp4',
        '',
      ];
      const selectedMime = mimeTypes.find((m) => m === '' || MediaRecorder.isTypeSupported(m));
      const options = selectedMime ? { mimeType: selectedMime } : {};

      const mediaRecorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const mimeType = mediaRecorder.mimeType || 'audio/webm';
        const finalBlob = new Blob(audioChunksRef.current, { type: mimeType });
        setAudioBlob(finalBlob);
        const objectUrl = URL.createObjectURL(finalBlob);
        setAudioUrl(objectUrl);

        // Ensure tracks are released upon recorder stop
        releaseMediaStream();
        stopTimer();
      };

      mediaRecorder.onerror = (event) => {
        setError(`Recording error: ${event.error?.message || 'Unknown recorder error'}`);
        releaseMediaStream();
        stopTimer();
        setIsRecording(false);
      };

      // Collect data slices every 250ms
      mediaRecorder.start(250);
      setIsRecording(true);

      // Start duration counter
      const startTime = Date.now();
      timerIntervalRef.current = setInterval(() => {
        const elapsedSec = Math.floor((Date.now() - startTime) / 1000);
        setRecordingDuration(elapsedSec);
      }, 1000);
    } catch (err) {
      const errorMsg =
        err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError'
          ? 'Microphone permission was denied by the user.'
          : `Failed to access microphone: ${err.message}`;
      setError(errorMsg);
      releaseMediaStream();
      stopTimer();
      setIsRecording(false);
      throw err;
    }
  }, [isSupported, audioUrl, releaseMediaStream, stopTimer]);

  /**
   * Stop active recording and finalize audio Blob.
   */
  const stopRecording = useCallback(() => {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state !== 'inactive'
    ) {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
    stopTimer();
  }, [stopTimer]);

  /**
   * Reset recording state and clear cached blob/URL.
   */
  const resetRecording = useCallback(() => {
    if (isRecording) {
      stopRecording();
    }
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
      setAudioUrl(null);
    }
    setAudioBlob(null);
    setRecordingDuration(0);
    setError(null);
    audioChunksRef.current = [];
  }, [isRecording, stopRecording, audioUrl]);

  // Clean up all resources when component unmounts
  useEffect(() => {
    return () => {
      stopTimer();
      if (
        mediaRecorderRef.current &&
        mediaRecorderRef.current.state !== 'inactive'
      ) {
        mediaRecorderRef.current.stop();
      }
      releaseMediaStream();
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, [stopTimer, releaseMediaStream, audioUrl]);

  return {
    isRecording,
    audioBlob,
    audioUrl,
    recordingDuration,
    error,
    isSupported,
    startRecording,
    stopRecording,
    resetRecording,
  };
}

export default useAudioRecorder;
