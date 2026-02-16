import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { apiFetch } from '../api'
import ContextualDialog from './ContextualDialog'
import ConfirmDialog from './ConfirmDialog'

/**
 * OnboardingWizard - Interactive contextual guidance that doesn't block the UI
 * Shows on first visit, tracks completion in database
 * Guides user through creating their first project with contextual tooltips
 */
function OnboardingWizard({ onComplete }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [currentStep, setCurrentStep] = useState(0)
  const [ldrawStats, setLdrawStats] = useState(null)
  const [isDownloading, setIsDownloading] = useState(false)
  const [projectCreated, setProjectCreated] = useState(false)
  const [showConfirmDismiss, setShowConfirmDismiss] = useState(false)

  useEffect(() => {
    checkLdrawStatus()
  }, [])

  // Check if user has created a project (poll /api/projects)
  useEffect(() => {
    if (currentStep >= 4 && currentStep < 7 && !projectCreated) {
      const checkProjects = async () => {
        try {
          const r = await apiFetch('/api/projects')
          if (r.ok) {
            const projects = await r.json()
            if (projects && projects.length > 0) {
              setProjectCreated(true)
              // Auto-advance to project guidance step after project creation
              setCurrentStep(7)
            }
          }
        } catch (e) {
          console.error('Failed to check projects:', e)
        }
      }
      
      // Poll every 2 seconds while on project creation steps
      const interval = setInterval(checkProjects, 2000)
      return () => clearInterval(interval)
    }
  }, [currentStep, projectCreated])

  const checkLdrawStatus = async () => {
    try {
      const r = await apiFetch('/api/ldraw/stats')
      if (r.ok) {
        setLdrawStats(await r.json())
      }
    } catch (e) {
      console.error('Failed to check LDraw status:', e)
    }
  }

  const handleDownloadLdraw = async () => {
    setIsDownloading(true)
    try {
      const r = await apiFetch('/api/ldraw/download', { method: 'POST' })
      if (r.ok) {
        await checkLdrawStatus()
      }
    } catch (e) {
      console.error('Failed to download LDraw:', e)
    } finally {
      setIsDownloading(false)
    }
  }

  const handleComplete = async () => {
    try {
      // Mark onboarding as complete in database
      await apiFetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ onboarding_wizard_complete: true })
      })
      onComplete()
    } catch (e) {
      console.error('Failed to mark onboarding complete:', e)
      onComplete() // Complete anyway to not block user
    }
  }

  const handleSkip = () => {
    setShowConfirmDismiss(true)
  }

  const handleConfirmDismiss = () => {
    setShowConfirmDismiss(false)
    handleComplete()
  }

  const handleCancelDismiss = () => {
    setShowConfirmDismiss(false)
  }

  const steps = [
    {
      title: 'Welcome to BrickGen! 🧱',
      position: 'top-right',
      content: (
        <div className="space-y-3">
          <h3 className="text-lg font-bold text-dk-5">Welcome to BrickGen!</h3>
          <p className="text-sm text-dk-5/90">
            BrickGen helps you convert LEGO sets from Rebrickable into 3D-printable STL files.
          </p>
          <p className="text-sm text-dk-5/90">
            Let's get you set up in just a few steps!
          </p>
          <button
            onClick={() => setCurrentStep(1)}
            className="w-full px-4 py-2 bg-mint text-dk-1 rounded-lg font-medium hover:opacity-90 transition text-sm"
          >
            Get Started
          </button>
        </div>
      )
    },
    {
      title: 'Download LDraw Library',
      position: 'bottom',
      targetSelector: '[href="/settings"]',
      highlight: 'settings',
      content: (
        <div className="space-y-3">
          <h3 className="text-lg font-bold text-dk-5">Download LDraw Library</h3>
          <p className="text-sm text-dk-5/90">
            The LDraw library contains 3D models for LEGO parts (~40MB).
          </p>
          {ldrawStats && (
            <div className={`p-3 rounded-lg border text-sm ${ldrawStats.exists ? 'bg-mint/10 border-mint/30' : 'bg-amber-500/10 border-amber-500/30'}`}>
              <div className="flex items-center gap-2">
                <span className={`text-base ${ldrawStats.exists ? 'text-mint' : 'text-amber-400'}`}>
                  {ldrawStats.exists ? '✓' : '⚠'}
                </span>
                <span className="font-medium text-dk-5">
                  {ldrawStats.exists ? 'Library Downloaded' : 'Library Not Downloaded'}
                </span>
              </div>
              {ldrawStats.exists && (
                <p className="text-xs text-dk-5/80 mt-1">
                  {ldrawStats.part_count?.toLocaleString()} parts ready
                </p>
              )}
            </div>
          )}
          <div className="flex gap-2">
            {!ldrawStats?.exists ? (
              <button
                onClick={handleDownloadLdraw}
                disabled={isDownloading}
                className="flex-1 px-4 py-2 bg-mint text-dk-1 rounded-lg font-medium hover:opacity-90 disabled:opacity-50 transition text-sm"
              >
                {isDownloading ? 'Downloading...' : 'Download Now'}
              </button>
            ) : (
              <button
                onClick={() => setCurrentStep(2)}
                className="flex-1 px-4 py-2 bg-mint text-dk-1 rounded-lg font-medium hover:opacity-90 transition text-sm"
              >
                Continue
              </button>
            )}
          </div>
          <p className="text-xs text-dk-5/60 text-center">
            👆 Click Settings to download later from Cache tab
          </p>
        </div>
      )
    },
    {
      title: 'LDView Settings (Optional)',
      position: 'bottom',
      targetSelector: '[href="/settings"]',
      highlight: 'settings',
      content: (
        <div className="space-y-3">
          <h3 className="text-lg font-bold text-dk-5">LDView Settings</h3>
          <p className="text-sm text-dk-5/90">
            LDView controls STL quality. Defaults work great for most users.
          </p>
          <div className="text-xs text-dk-5/80 space-y-1">
            <p>• Higher curve quality = smoother parts</p>
            <p>• Quality studs add realistic detail</p>
            <p>• Textures make parts look authentic</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => navigate('/settings')}
              className="flex-1 px-4 py-2 bg-dk-3 text-dk-5 rounded-lg hover:bg-dk-3/80 transition text-sm"
            >
              Customize
            </button>
            <button
              onClick={() => setCurrentStep(3)}
              className="flex-1 px-4 py-2 bg-mint text-dk-1 rounded-lg font-medium hover:opacity-90 transition text-sm"
            >
              Continue
            </button>
          </div>
        </div>
      )
    },
    {
      title: 'Create Your First Project',
      position: 'top-right',
      content: (
        <div className="space-y-3">
          <h3 className="text-lg font-bold text-dk-5">Create Your First Project</h3>
          <p className="text-sm text-dk-5/90">
            Let's create a project! We'll guide you through:
          </p>
          <ol className="text-sm text-dk-5/80 space-y-1 list-decimal list-inside">
            <li>Searching for a LEGO set</li>
            <li>Viewing the set details</li>
            <li>Creating a project from the set</li>
          </ol>
          <button
            onClick={() => {
              setCurrentStep(4)
              navigate('/')
            }}
            className="w-full px-4 py-2 bg-mint text-dk-1 rounded-lg font-medium hover:opacity-90 transition text-sm"
          >
            Let's Get Started!
          </button>
        </div>
      )
    },
    {
      title: 'Search for a Set',
      position: 'top-right', // Changed from 'top' to keep as side wizard
      // Remove targetSelector to keep as side wizard instead of pointing to search box
      content: (
        <div className="space-y-3">
          <h3 className="text-lg font-bold text-dk-5">Step 1: Search</h3>
          <p className="text-sm text-dk-5/90">
            Use the search box below to find a LEGO set by name or number (e.g., "21348-1").
          </p>
          <p className="text-xs text-dk-5/70">
            💡 Find set numbers on <a href="https://rebrickable.com" target="_blank" rel="noopener noreferrer" className="text-mint hover:underline">Rebrickable</a>
          </p>
        </div>
      ),
      showOnPages: ['/'],
      highlightTarget: 'input[type="text"]' // Add highlight instead of positioning to it
    },
    {
      title: 'View Set Details',
      position: 'top-right',
      content: (
        <div className="space-y-3">
          <h3 className="text-lg font-bold text-dk-5">Step 2: Select Set</h3>
          <p className="text-sm text-dk-5/90">
            Click on a set from the results to view its details and create a project.
          </p>
        </div>
      ),
      showOnPages: ['/']
    },
    {
      title: 'Create Your Project',
      position: 'top-right',
      content: (
        <div className="space-y-3">
          <h3 className="text-lg font-bold text-dk-5">Step 3: Create Project</h3>
          <p className="text-sm text-dk-5/90">
            Scroll down, enter a project name, and click "Create project".
          </p>
          <p className="text-xs text-dk-5/70">
            📝 Give it a descriptive name to identify it later
          </p>
        </div>
      ),
      showOnPages: ['/set/']
    },
    {
      title: 'Open Your Project',
      position: 'top-right',
      content: (
        <div className="space-y-3">
          <h3 className="text-lg font-bold text-dk-5">Step 4: Open Project</h3>
          <p className="text-sm text-dk-5/90">
            Great! Your project was created. Now click on "Projects" in the menu to view it.
          </p>
          <button
            onClick={() => {
              navigate('/projects')
              setCurrentStep(8)
            }}
            className="w-full px-4 py-2 bg-mint text-dk-1 rounded-lg font-medium hover:opacity-90 transition text-sm"
          >
            Go to Projects
          </button>
        </div>
      ),
      showOnPages: ['/set/', '/']
    },
    {
      title: 'Open Your Project',
      position: 'top-right',
      content: (
        <div className="space-y-3">
          <h3 className="text-lg font-bold text-dk-5">Step 5: Select Project</h3>
          <p className="text-sm text-dk-5/90">
            Click on your newly created project to open it.
          </p>
        </div>
      ),
      showOnPages: ['/projects']
    },
    {
      title: 'Generate STL Files',
      position: 'top-right',
      content: (
        <div className="space-y-3">
          <h3 className="text-lg font-bold text-dk-5">Step 6: Generate STLs</h3>
          <p className="text-sm text-dk-5/90">
            Click "Create Job" or "Quick Generate" to start generating 3D-printable STL files for your LEGO parts.
          </p>
          <div className="text-xs text-dk-5/70 space-y-1">
            <p>• <strong>Quick Generate</strong>: Uses default settings</p>
            <p>• <strong>Create Job</strong>: Customize settings first</p>
          </div>
          <button
            onClick={() => setCurrentStep(10)}
            className="w-full px-4 py-2 bg-mint text-dk-1 rounded-lg font-medium hover:opacity-90 transition text-sm"
          >
            Continue
          </button>
        </div>
      ),
      showOnPages: ['/projects/']
    },
    {
      title: 'Onboarding Complete!',
      position: 'top-right',
      content: (
        <div className="space-y-3">
          <h3 className="text-lg font-bold text-dk-5">You're All Set! 🎉</h3>
          <p className="text-sm text-dk-5/90">
            You've completed the onboarding and learned the basics!
          </p>
          <div className="text-xs text-dk-5/80 space-y-1">
            <p>✓ Downloaded LDraw library</p>
            <p>✓ Configured settings</p>
            <p>✓ Created first project</p>
            <p>✓ Learned how to generate STLs</p>
          </div>
          <button
            onClick={handleComplete}
            className="w-full px-4 py-2 bg-mint text-dk-1 rounded-lg font-medium hover:opacity-90 transition text-sm"
          >
            Finish Onboarding
          </button>
        </div>
      )
    }
  ]

  const currentStepData = steps[currentStep]
  
  // Check if wizard should be shown on current page
  const shouldShowOnCurrentPage = () => {
    if (!currentStepData.showOnPages) return true
    return currentStepData.showOnPages.some(page => location.pathname.startsWith(page))
  }
  
  // Auto-advance steps based on location
  useEffect(() => {
    if (currentStep === 4 && location.pathname === '/') {
      // Already on search page, stay on step 4
    } else if (currentStep === 4 && location.pathname.startsWith('/set/')) {
      // User navigated to set detail, advance to step 5
      setCurrentStep(5)
    } else if (currentStep === 5 && location.pathname === '/') {
      // User went back to search, go back to step 4
      setCurrentStep(4)
    } else if (currentStep === 7 && location.pathname.startsWith('/projects/') && location.pathname !== '/projects') {
      // User opened a specific project, advance to step 9 (generate STLs)
      setCurrentStep(9)
    } else if (currentStep === 8 && location.pathname.startsWith('/projects/') && location.pathname !== '/projects') {
      // User opened a specific project from projects page, advance to step 9
      setCurrentStep(9)
    }
  }, [location.pathname, currentStep])

  // Don't render if we're on a page that shouldn't show the wizard for this step
  if (!shouldShowOnCurrentPage()) {
    return null
  }

  return (
    <>
      {/* Spotlight effect for highlighted elements */}
      {currentStepData.highlight === 'settings' && (
        <style dangerouslySetInnerHTML={{ __html: `
          nav a[href="/settings"] {
            position: relative;
            z-index: 50;
            box-shadow: 0 0 0 4px rgba(0, 217, 255, 0.5), 0 0 30px rgba(0, 217, 255, 0.3);
            animation: pulse-glow 2s infinite;
          }
          @keyframes pulse-glow {
            0%, 100% { box-shadow: 0 0 0 4px rgba(0, 217, 255, 0.5), 0 0 30px rgba(0, 217, 255, 0.3); }
            50% { box-shadow: 0 0 0 6px rgba(0, 217, 255, 0.7), 0 0 40px rgba(0, 217, 255, 0.5); }
          }
        ` }} />
      )}
      
      {/* Highlight effect for other target elements */}
      {currentStepData.highlightTarget && (
        <style dangerouslySetInnerHTML={{ __html: `
          ${currentStepData.highlightTarget} {
            box-shadow: 0 0 0 3px rgba(0, 217, 255, 0.4), 0 0 20px rgba(0, 217, 255, 0.2);
            animation: pulse-highlight 2s infinite;
          }
          @keyframes pulse-highlight {
            0%, 100% { box-shadow: 0 0 0 3px rgba(0, 217, 255, 0.4), 0 0 20px rgba(0, 217, 255, 0.2); }
            50% { box-shadow: 0 0 0 5px rgba(0, 217, 255, 0.6), 0 0 30px rgba(0, 217, 255, 0.4); }
          }
        ` }} />
      )}

      {/* Contextual dialog instead of blocking modal */}
      <ContextualDialog
        position={currentStepData.position}
        targetSelector={currentStepData.targetSelector}
        onDismiss={handleSkip}
        showDismiss={true}
      >
        {currentStepData.content}
        
        {/* Progress dots */}
        <div className="flex gap-1.5 justify-center mt-3 pt-3 border-t border-dk-3">
          {steps.map((_, idx) => (
            <div
              key={idx}
              className={`w-2 h-2 rounded-full transition-colors ${
                idx === currentStep ? 'bg-mint' : idx < currentStep ? 'bg-mint/50' : 'bg-dk-3'
              }`}
              title={`Step ${idx + 1}`}
            />
          ))}
        </div>
      </ContextualDialog>

      {/* Confirmation dialog for dismissing wizard */}
      <ConfirmDialog
        isOpen={showConfirmDismiss}
        title="Exit Onboarding Wizard?"
        message="Are you sure you want to exit the onboarding wizard? You can restart it later from Settings."
        confirmText="Exit Wizard"
        cancelText="Continue Learning"
        onConfirm={handleConfirmDismiss}
        onCancel={handleCancelDismiss}
      />
    </>
  )
}

export default OnboardingWizard
