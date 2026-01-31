'use client';

import { useState } from 'react';
import { Upload, Download, FileText, AlertCircle, CheckCircle2, Loader2, X } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface ImportDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

interface ImportResult {
  success: boolean;
  categories_created: number;
  services_created: number;
  errors: string[];
  total_rows_processed: number;
}

export function ImportDialog({ open, onClose, onSuccess }: ImportDialogProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.name.endsWith('.csv')) {
        setFile(droppedFile);
        setResult(null);
      } else {
        toast.error('Please upload a CSV file');
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setResult(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      toast.error('Please select a file');
      return;
    }

    try {
      setIsUploading(true);
      const formData = new FormData();
      formData.append('file', file);

      const { data } = await apiClient.post('/catalog/import', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setResult(data);

      if (data.success) {
        toast.success(
          `Import successful! ${data.categories_created} categories and ${data.services_created} services created.`
        );
        if (data.errors.length === 0) {
          setTimeout(() => {
            onSuccess();
            handleClose();
          }, 2000);
        }
      }
    } catch (error: any) {
      console.error('Import error:', error);
      toast.error(error.response?.data?.detail || 'Failed to import file');
    } finally {
      setIsUploading(false);
    }
  };

  const handleClose = () => {
    setFile(null);
    setResult(null);
    setDragActive(false);
    onClose();
  };

  const downloadTemplate = () => {
    const template = `type,category_name,name,description,base_price,duration_minutes,display_order
category,,Haircut & Styling,Hair cutting and styling services,,,1
service,Haircut & Styling,Basic Haircut,Simple haircut for men,300,15,1
service,Haircut & Styling,Premium Haircut,Premium styling with consultation,500,30,2
category,,Hair Color & Treatment,Hair coloring and treatment services,,,2
service,Hair Color & Treatment,Full Hair Color,Complete hair coloring,2500,120,1
service,Hair Color & Treatment,Highlights,Partial highlights,1800,90,2`;

    const blob = new Blob([template], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'catalog_import_template.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5" />
            Import Categories & Services
          </DialogTitle>
          <DialogDescription>
            Upload a CSV file to bulk import your catalog. Download the template to see the required format.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Download Template Button */}
          <div className="flex justify-end">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={downloadTemplate}
              className="gap-2"
            >
              <Download className="h-4 w-4" />
              Download Template
            </Button>
          </div>

          {/* File Upload Area */}
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              dragActive
                ? 'border-primary bg-primary/5'
                : 'border-gray-300 hover:border-gray-400'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            {file ? (
              <div className="flex items-center justify-center gap-3">
                <FileText className="h-8 w-8 text-primary" />
                <div className="text-left">
                  <p className="font-medium text-gray-900">{file.name}</p>
                  <p className="text-sm text-gray-500">
                    {(file.size / 1024).toFixed(2)} KB
                  </p>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => {
                    setFile(null);
                    setResult(null);
                  }}
                  className="ml-auto"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ) : (
              <>
                <Upload className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                <p className="text-gray-600 mb-2">
                  Drag and drop your CSV file here, or click to browse
                </p>
                <input
                  type="file"
                  accept=".csv"
                  onChange={handleFileChange}
                  className="hidden"
                  id="file-upload"
                />
                <label htmlFor="file-upload">
                  <Button type="button" variant="outline" className="cursor-pointer" asChild>
                    <span>Select File</span>
                  </Button>
                </label>
              </>
            )}
          </div>

          {/* Format Instructions */}
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="text-sm">
              <strong>CSV Format:</strong>
              <ul className="list-disc list-inside mt-2 space-y-1">
                <li>
                  <strong>type:</strong> "category" or "service"
                </li>
                <li>
                  <strong>category_name:</strong> Required for services (must match existing category)
                </li>
                <li>
                  <strong>name:</strong> Name of the category or service
                </li>
                <li>
                  <strong>description:</strong> Description (optional)
                </li>
                <li>
                  <strong>base_price:</strong> Price in rupees (e.g., 300.00) - for services only
                </li>
                <li>
                  <strong>duration_minutes:</strong> Duration (e.g., 30) - for services only
                </li>
                <li>
                  <strong>display_order:</strong> Display order (integer)
                </li>
              </ul>
            </AlertDescription>
          </Alert>

          {/* Import Results */}
          {result && (
            <Alert variant={result.errors.length > 0 ? 'destructive' : 'default'}>
              {result.errors.length === 0 ? (
                <CheckCircle2 className="h-4 w-4" />
              ) : (
                <AlertCircle className="h-4 w-4" />
              )}
              <AlertDescription>
                <div className="space-y-2">
                  <div>
                    <strong>Import Results:</strong>
                    <ul className="list-disc list-inside mt-1">
                      <li>{result.categories_created} categories created</li>
                      <li>{result.services_created} services created</li>
                      <li>{result.total_rows_processed} rows processed</li>
                    </ul>
                  </div>
                  {result.errors.length > 0 && (
                    <div className="mt-3">
                      <strong className="text-red-600">Errors:</strong>
                      <div className="mt-1 max-h-32 overflow-y-auto text-sm">
                        {result.errors.map((error, idx) => (
                          <div key={idx} className="text-red-600">
                            • {error}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={handleClose}>
            {result ? 'Close' : 'Cancel'}
          </Button>
          {!result && (
            <Button
              type="button"
              onClick={handleUpload}
              disabled={!file || isUploading}
            >
              {isUploading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Import
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
