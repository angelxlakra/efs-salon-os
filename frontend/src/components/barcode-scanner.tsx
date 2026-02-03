'use client';

import { useEffect, useRef, useState } from 'react';
import { Html5Qrcode } from 'html5-qrcode';
import { Camera, X, AlertCircle, Check, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';

interface ScannedItem {
  barcode: string;
  timestamp: number;
}

interface BarcodeScannerProps {
  onScan: (barcode: string) => void;
  onClose: () => void;
  autoClose?: boolean;
  disabled?: boolean;
}

export function BarcodeScanner({ onScan, onClose, autoClose = false, disabled = false }: BarcodeScannerProps) {
  const [isScanning, setIsScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cameras, setCameras] = useState<{ id: string; label: string }[]>([]);
  const [selectedCamera, setSelectedCamera] = useState<string>('');
  const [scannedItems, setScannedItems] = useState<ScannedItem[]>([]);
  const [scanFeedback, setScanFeedback] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [permissionDenied, setPermissionDenied] = useState(false);
  const [isBackCamera, setIsBackCamera] = useState(true); // Track if using back camera
  const scannerRef = useRef<Html5Qrcode | null>(null);
  const scannerIdRef = useRef('barcode-scanner-' + Math.random().toString(36).substr(2, 9));
  const lastScanRef = useRef<string>('');

  const onScanRef = useRef(onScan);
  const disabledRef = useRef(disabled);

  useEffect(() => {
    onScanRef.current = onScan;
  }, [onScan]);

  useEffect(() => {
    disabledRef.current = disabled;
  }, [disabled]);

  useEffect(() => {
    initializeCamera();

    return () => {
      // Cleanup scanner on unmount
      if (scannerRef.current) {
        scannerRef.current
          .stop()
          .catch((err) => console.debug('Error stopping scanner on unmount:', err));
      }
    };
  }, []);

  const initializeCamera = async () => {
    setIsInitializing(true);
    setError(null);
    setPermissionDenied(false);

    try {
      // Check if browser supports camera API
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setError('Your browser does not support camera access. Please use a modern browser like Chrome or Safari.');
        setIsInitializing(false);
        return;
      }

      // Check if we're on HTTPS or localhost
      const isSecure = window.location.protocol === 'https:' ||
                      window.location.hostname === 'localhost' ||
                      window.location.hostname === '127.0.0.1';

      // Request camera permission explicitly
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' }
      });

      // Stop the test stream immediately
      stream.getTracks().forEach(track => track.stop());

      // Now get the list of cameras
      const devices = await Html5Qrcode.getCameras();

      if (devices && devices.length > 0) {
        const cameraList = devices.map((device) => ({
          id: device.id,
          label: device.label || `Camera ${device.id}`,
        }));
        setCameras(cameraList);

        // Prefer back camera on mobile
        const backCamera = devices.find((d) =>
          d.label.toLowerCase().includes('back') ||
          d.label.toLowerCase().includes('rear') ||
          d.label.toLowerCase().includes('environment')
        );
        const cameraId = backCamera?.id || devices[0].id;
        setSelectedCamera(cameraId);

        // Determine if selected camera is back camera
        const isBack = backCamera ? true : !devices[0].label.toLowerCase().includes('front');
        setIsBackCamera(isBack);

        // Auto-start scanning with the selected camera
        setTimeout(() => {
          startScanningWithCamera(cameraId);
        }, 500);
      } else {
        setError('No cameras found on this device');
      }
    } catch (err: any) {
      console.error('Error initializing camera:', err);

      // Check if this is an HTTPS requirement error
      const isSecure = window.location.protocol === 'https:' ||
                      window.location.hostname === 'localhost' ||
                      window.location.hostname === '127.0.0.1';

      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setPermissionDenied(true);
        if (!isSecure) {
          setError('Camera access requires HTTPS or localhost. Your browser is blocking camera access on HTTP connections for security reasons.');
        } else {
          setError('Camera access was denied. Please allow camera permissions in your browser settings and try again.');
        }
      } else if (err.name === 'NotFoundError') {
        setError('No camera found on this device');
      } else if (err.name === 'NotReadableError') {
        setError('Camera is already in use by another application');
      } else if (err.name === 'NotSupportedError' || err.name === 'TypeError') {
        if (!isSecure) {
          setError('Camera access requires HTTPS. Most modern browsers block camera on HTTP for security. Please access via HTTPS or localhost.');
        } else {
          setError('Camera access is not supported in this browser or context');
        }
      } else {
        setError(err.message || 'Could not access camera. Please check your browser permissions.');
      }
    } finally {
      setIsInitializing(false);
    }
  };

  const startScanningWithCamera = async (cameraId: string) => {
    if (!cameraId) {
      setError('No camera selected');
      return;
    }

    try {
      setError(null);

      // Determine if this is a back camera based on camera ID and label
      const camera = cameras.find(c => c.id === cameraId);
      const isBack = camera ?
        (camera.label.toLowerCase().includes('back') ||
         camera.label.toLowerCase().includes('rear') ||
         camera.label.toLowerCase().includes('environment')) :
        true; // Default to back camera if can't determine
      setIsBackCamera(isBack);

      const scanner = new Html5Qrcode(scannerIdRef.current);
      scannerRef.current = scanner;

      await scanner.start(
        cameraId,
        {
          fps: 10,
          qrbox: { width: 250, height: 250 },
          aspectRatio: 1.0,
        },
        (decodedText) => {
          // Successfully scanned
          console.log('Scanned barcode:', decodedText);

          // Prevent duplicate scans within 3 seconds
          if (lastScanRef.current === decodedText) {
            return;
          }

          lastScanRef.current = decodedText;
          setTimeout(() => {
            lastScanRef.current = '';
          }, 3000);

          // Check if this barcode was already scanned in the last 5 seconds
          const recentScan = scannedItems.find(
            item => item.barcode === decodedText && Date.now() - item.timestamp < 5000
          );

          if (recentScan) {
            return; // Skip duplicate
          }

          // Add to scanned items list (only if not disabled)
          if (!disabledRef.current) {
            setScannedItems(prev => [...prev, { barcode: decodedText, timestamp: Date.now() }]);

            // Show visual feedback
            setScanFeedback(true);
            setTimeout(() => setScanFeedback(false), 500);

            // Call parent callback using ref to avoid stale closure
            onScanRef.current(decodedText);

            // Only stop if autoClose is true
            if (autoClose) {
              stopScanning();
            }
          }
        },
        (errorMessage) => {
          // Scanning error (can be ignored, happens frequently)
          // console.log('Scan error:', errorMessage);
        }
      );

      setIsScanning(true);
    } catch (err: any) {
      console.error('Error starting scanner:', err);
      setError(err.message || 'Failed to start camera scanner');
      setIsScanning(false);
    }
  };

  const stopScanning = async () => {
    if (scannerRef.current && isScanning) {
      try {
        await scannerRef.current.stop();
        scannerRef.current.clear();
        scannerRef.current = null;
        setIsScanning(false);
      } catch (err) {
        console.error('Error stopping scanner:', err);
      }
    }
  };

  const startScanning = async () => {
    await startScanningWithCamera(selectedCamera);
  };

  const handleClose = async () => {
    await stopScanning();
    onClose();
  };

  const handleCameraChange = async (cameraId: string) => {
    if (isScanning) {
      await stopScanning();
    }
    setSelectedCamera(cameraId);

    // Update back camera state based on selected camera
    const camera = cameras.find(c => c.id === cameraId);
    const isBack = camera ?
      (camera.label.toLowerCase().includes('back') ||
       camera.label.toLowerCase().includes('rear') ||
       camera.label.toLowerCase().includes('environment')) :
      true;
    setIsBackCamera(isBack);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4 overflow-y-auto">
      <Card className="w-full max-w-3xl my-auto">
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Scan Barcode</h3>
            <Button variant="ghost" size="icon" onClick={handleClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>

          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                <div className="space-y-2">
                  <p>{error}</p>
                  {error.includes('HTTPS') && (
                    <div className="text-xs space-y-2 mt-3 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded">
                      <p className="font-semibold">Quick Fix Options:</p>
                      <div className="space-y-2">
                        <div>
                          <p className="font-medium">Option 1: Use Desktop Scanner</p>
                          <p className="text-muted-foreground">Use a USB barcode scanner on a desktop/laptop connected to the local network</p>
                        </div>
                        <div>
                          <p className="font-medium">Option 2: Manual Entry</p>
                          <p className="text-muted-foreground">Close this dialog and type the barcode manually</p>
                        </div>
                        <div>
                          <p className="font-medium">Option 3: Enable HTTPS (Recommended)</p>
                          <p className="text-muted-foreground">Contact your system administrator to set up HTTPS for the local server</p>
                        </div>
                      </div>
                    </div>
                  )}
                  {permissionDenied && !error.includes('HTTPS') && (
                    <div className="text-xs space-y-1 mt-2">
                      <p className="font-semibold">To enable camera access:</p>
                      <ul className="list-disc list-inside space-y-1 pl-2">
                        <li>On Chrome/Safari: Tap the lock/info icon in the address bar</li>
                        <li>Find "Camera" or "Permissions" settings</li>
                        <li>Select "Allow" for camera access</li>
                        <li>Refresh the page and try again</li>
                      </ul>
                    </div>
                  )}
                  <Button
                    onClick={initializeCamera}
                    variant="outline"
                    size="sm"
                    className="mt-3"
                  >
                    <Camera className="mr-2 h-4 w-4" />
                    Try Again
                  </Button>
                </div>
              </AlertDescription>
            </Alert>
          )}

          {cameras.length > 1 && !isScanning && (
            <div className="mb-4">
              <label className="text-sm font-medium mb-2 block">Select Camera:</label>
              <select
                value={selectedCamera}
                onChange={(e) => handleCameraChange(e.target.value)}
                className="w-full p-2 border rounded-md"
              >
                {cameras.map((camera) => (
                  <option key={camera.id} value={camera.id}>
                    {camera.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="relative bg-black rounded-lg overflow-hidden" style={{ height: '400px', maxHeight: '50vh' }}>
            <style dangerouslySetInnerHTML={{
              __html: `
                #${scannerIdRef.current} img {
                  display: none !important;
                }
                #${scannerIdRef.current} video {
                  width: 100% !important;
                  height: 100% !important;
                  max-height: 50vh !important;
                  object-fit: cover !important;
                  display: block !important;
                }
                #${scannerIdRef.current}__scan_region {
                  border: none !important;
                }
                #${scannerIdRef.current} {
                  height: 100% !important;
                }
              `
            }} />
            <div
              id={scannerIdRef.current}
              className="w-full h-full"
              style={{
                transform: isBackCamera ? 'none' : 'scaleX(-1)', // Mirror only for front camera
              }}
            />

            {isInitializing && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/50">
                <div className="text-center text-white">
                  <Loader2 className="h-8 w-8 animate-spin mx-auto mb-2" />
                  <p className="text-sm">Requesting camera access...</p>
                </div>
              </div>
            )}

            {!isScanning && !error && !isInitializing && (
              <div className="absolute inset-0 flex items-center justify-center">
                <Button onClick={startScanning} size="lg">
                  <Camera className="mr-2 h-5 w-5" />
                  Start Scanner
                </Button>
              </div>
            )}

            {scanFeedback && (
              <div className="absolute inset-0 bg-green-500/30 flex items-center justify-center pointer-events-none">
                <div className="bg-green-600 text-white px-4 py-2 rounded-lg font-semibold">
                  ✓ Scanned!
                </div>
              </div>
            )}

            {disabled && isScanning && (
              <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
                <div className="bg-yellow-600 text-white px-6 py-3 rounded-lg font-semibold text-center">
                  <AlertCircle className="h-6 w-6 mx-auto mb-2" />
                  Scanning Paused
                  <p className="text-sm font-normal mt-1">Complete the product details to resume</p>
                </div>
              </div>
            )}
          </div>

          {isScanning && (
            <div className="mt-4 space-y-3">
              <p className="text-sm text-muted-foreground text-center">
                Position the barcode within the square frame
                {!isBackCamera && ' • Front camera is mirrored for easier viewing'}
              </p>

              {scannedItems.length > 0 && (
                <div className="border rounded-lg p-3 max-h-40 overflow-y-auto">
                  <div className="flex items-center gap-2 mb-2">
                    <Check className="h-4 w-4 text-green-600" />
                    <span className="text-sm font-medium">Scanned Items ({scannedItems.length})</span>
                  </div>
                  <div className="space-y-1">
                    {scannedItems.slice().reverse().map((item, index) => (
                      <div key={item.timestamp} className="flex items-center gap-2 text-sm">
                        <Badge variant="secondary" className="font-mono text-xs">
                          {item.barcode}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {new Date(item.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <Button onClick={handleClose} className="w-full">
                <Check className="mr-2 h-4 w-4" />
                Done Scanning
              </Button>
            </div>
          )}

          <div className="mt-4 text-xs text-muted-foreground text-center">
            <p>Supports: EAN, UPC, Code 128, Code 39, QR Code, and more</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
