'use client';

import { useEffect, useRef, useState } from 'react';
import { Html5Qrcode } from 'html5-qrcode';
import { Camera, X, AlertCircle, Check } from 'lucide-react';
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
    // Get available cameras
    Html5Qrcode.getCameras()
      .then((devices) => {
        if (devices && devices.length > 0) {
          const cameraList = devices.map((device) => ({
            id: device.id,
            label: device.label || `Camera ${device.id}`,
          }));
          setCameras(cameraList);

          // Prefer back camera on mobile
          const backCamera = devices.find((d) =>
            d.label.toLowerCase().includes('back') ||
            d.label.toLowerCase().includes('rear')
          );
          const cameraId = backCamera?.id || devices[0].id;
          setSelectedCamera(cameraId);

          // Auto-start scanning with the selected camera
          setTimeout(() => {
            startScanningWithCamera(cameraId);
          }, 500);
        } else {
          setError('No cameras found on this device');
        }
      })
      .catch((err) => {
        console.error('Error getting cameras:', err);
        setError('Could not access cameras. Please allow camera permissions.');
      });

    return () => {
      // Cleanup scanner on unmount
      if (scannerRef.current) {
        scannerRef.current
          .stop()
          .catch((err) => console.debug('Error stopping scanner on unmount:', err));
      }
    };
  }, []);

  const startScanningWithCamera = async (cameraId: string) => {
    if (!cameraId) {
      setError('No camera selected');
      return;
    }

    try {
      setError(null);
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
              <AlertDescription>{error}</AlertDescription>
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
                transform: 'scaleX(-1)', // Mirror the camera feed
              }}
            />

            {!isScanning && !error && (
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
                Position the barcode within the square frame • Camera is mirrored for easier scanning
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
