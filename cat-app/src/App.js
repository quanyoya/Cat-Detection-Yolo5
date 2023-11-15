import React, { useRef, useState, useEffect } from 'react';
import './App.css';

const interval = 10000;  // 10 s interval

function App() {
  const webcamRef = useRef(null);
  const canvasRef = useRef(null);
  const [detections, setDetections] = useState([]);
  const [isCapturing, setIsCapturing] = useState(false);
  const [circleColor, setCircleColor] = useState('black');


  useEffect(() => {
    const setupWebcam = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        if (webcamRef.current) {
          webcamRef.current.srcObject = stream;
          webcamRef.current.play();
        }
      } catch (error) {
        console.error('Error accessing the webcam', error);
      }
    };

    setupWebcam();
  }, []);

  // const captureImages = () => {
    // let count = 0;
    // const intervalId = setInterval(() => {
    //   if (count >= 5) {
    //     clearInterval(intervalId);
    //     return;
    //   }
    //   const canvas = canvasRef.current;
    //   canvas.toBlob(blob => {
    //     sendImageToBackend(blob);
    //   }, 'image/jpeg');
    //   count++;
    // }, interval);
  // };

  useEffect(() => {
    let intervalId;

    const captureImages = () => {
      const canvas = canvasRef.current;
      canvas.toBlob(blob => {
        sendImageToBackend(blob);
      }, 'image/jpeg');
    };

    if (isCapturing) {
      intervalId = setInterval(captureImages, interval);
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [isCapturing]);

  const sendImageToBackend = (blob) => {
    const formData = new FormData();
    formData.append('image', blob, 'image.jpg');
  
    fetch('http://127.0.0.1:5000/detect', {
      method: 'POST',
      body: formData
    })
    .then(response => response.json())
    .then(data => {
      // Assuming 'data' is an object that contains a 'detections' property which is a JSON string
      const results = JSON.parse(data.detections);
      setDetections(prevDetections => [...prevDetections, ...results]);
      
      if (data.cat_stay === 'sofa') {
        setCircleColor('red');
      } else if (data.cat_stay === 'table') {
        setCircleColor('green');
      } else {
        setCircleColor('black');
      }
    })
    .catch(error => {
      console.error('Error:', error);
    });
  };

  const drawWebcam = () => {
    const video = webcamRef.current;
    const canvas = canvasRef.current;
    const context = canvas.getContext('2d');

    if (video && video.readyState === video.HAVE_ENOUGH_DATA) {
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
    }
    requestAnimationFrame(drawWebcam);
  };

  // Add Start and Stop button handlers
  const startCapturing = () => setIsCapturing(true);
  const stopCapturing = () => setIsCapturing(false);

  return (
    <div className="App">
      <header className="App-header">

        <div id="webcam-container">
          <video ref={webcamRef} onPlay={drawWebcam} style={{ display: 'none' }} />
          <canvas ref={canvasRef} width="640" height="480" />
          <button onClick={startCapturing}>Start</button>
          <button onClick={stopCapturing}>Stop</button>
        </div>

        <div id="detection-results">
          {detections.map((detection, index) => (
            <div key={index} className="detection">
              <p>Object: {detection.name}</p>
              <p>Confidence: {(detection.confidence * 100).toFixed(2)}%</p>
              <p>Coordinates: ({detection.xmin.toFixed(2)}, {detection.ymin.toFixed(2)}) - ({detection.xmax.toFixed(2)}, {detection.ymax.toFixed(2)})</p>
            </div>
          ))}
        </div>

        <div style={{ width: '50px', height: '50px', borderRadius: '50%', backgroundColor: circleColor }}>
        </div>

      </header>
    </div>
  );
}

export default App;
