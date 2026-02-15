import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiFetch } from '../api'

/**
 * OnboardingWizard - Interactive overlay that guides users through initial setup
 * Shows on first visit, tracks completion in database
 */
function OnboardingWizard({ onComplete }) {
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState(0)
  const [ldrawStats, setLdrawStats] = useState(null)
  const [isDownloading, setIsDownloading] = useState(false)

  useEffect(() => {
    checkLdrawStatus()
  }, [])

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
    handleComplete()
  }

  const steps = [
    {
      title: 'Welcome to BrickGen! 🧱',
      content: (
        <div className="space-y-4">
          <p className="text-dk-5/90">
            BrickGen helps you convert LEGO sets from Rebrickable into 3D-printable STL files.
          </p>
          <p className="text-dk-5/90">
            Let's get you set up in just a few steps!
          </p>
          <div className="flex gap-3 mt-6">
            <button
              onClick={() => setCurrentStep(1)}
              className="flex-1 px-6 py-3 bg-mint text-dk-1 rounded-lg font-medium hover:opacity-90 transition"
            >
              Get Started
            </button>
            <button
              onClick={handleSkip}
              className="px-6 py-3 bg-dk-3 text-dk-5/80 rounded-lg hover:bg-dk-3/80 transition"
            >
              Skip
            </button>
          </div>
        </div>
      )
    },
    {
      title: 'Download LDraw Library',
      content: (
        <div className="space-y-4">
          <p className="text-dk-5/90">
            The LDraw library contains 3D models for LEGO parts. You need to download it once (~40MB).
          </p>
          {ldrawStats && (
            <div className={`p-4 rounded-lg border ${ldrawStats.exists ? 'bg-mint/10 border-mint/30' : 'bg-amber-500/10 border-amber-500/30'}`}>
              <div className="flex items-center gap-2 mb-2">
                <span className={`text-lg ${ldrawStats.exists ? 'text-mint' : 'text-amber-400'}`}>
                  {ldrawStats.exists ? '✓' : '⚠'}
                </span>
                <span className="font-medium text-dk-5">
                  {ldrawStats.exists ? 'Library Downloaded' : 'Library Not Downloaded'}
                </span>
              </div>
              {ldrawStats.exists && (
                <p className="text-sm text-dk-5/80">
                  {ldrawStats.part_count?.toLocaleString()} parts ready to use
                </p>
              )}
            </div>
          )}
          <div className="flex gap-3 mt-6">
            {!ldrawStats?.exists ? (
              <button
                onClick={handleDownloadLdraw}
                disabled={isDownloading}
                className="flex-1 px-6 py-3 bg-mint text-dk-1 rounded-lg font-medium hover:opacity-90 disabled:opacity-50 transition"
              >
                {isDownloading ? 'Downloading...' : 'Download Now'}
              </button>
            ) : (
              <button
                onClick={() => setCurrentStep(2)}
                className="flex-1 px-6 py-3 bg-mint text-dk-1 rounded-lg font-medium hover:opacity-90 transition"
              >
                Continue
              </button>
            )}
            <button
              onClick={() => setCurrentStep(0)}
              className="px-6 py-3 bg-dk-3 text-dk-5/80 rounded-lg hover:bg-dk-3/80 transition"
            >
              Back
            </button>
          </div>
          <p className="text-xs text-dk-5/60 text-center">
            You can also download later from Settings → Cache tab
          </p>
        </div>
      ),
      highlight: 'settings'
    },
    {
      title: 'Customize LDView Settings (Optional)',
      content: (
        <div className="space-y-4">
          <p className="text-dk-5/90">
            LDView settings control the quality of generated STL files. The defaults work great for most users.
          </p>
          <div className="p-4 rounded-lg bg-dk-3/50 border border-dk-3">
            <p className="text-sm text-dk-5/90 mb-2">
              <strong>Quick tips:</strong>
            </p>
            <ul className="text-sm text-dk-5/80 space-y-1 list-disc list-inside">
              <li>Higher curve quality = smoother parts (but larger files)</li>
              <li>Quality studs add realistic detail</li>
              <li>Textures make parts look more authentic</li>
            </ul>
          </div>
          <div className="flex gap-3 mt-6">
            <button
              onClick={() => navigate('/settings')}
              className="flex-1 px-6 py-3 bg-dk-3 text-dk-5 rounded-lg hover:bg-dk-3/80 transition"
            >
              Customize Settings
            </button>
            <button
              onClick={() => setCurrentStep(3)}
              className="flex-1 px-6 py-3 bg-mint text-dk-1 rounded-lg font-medium hover:opacity-90 transition"
            >
              Continue
            </button>
          </div>
          <p className="text-xs text-dk-5/60 text-center">
            You can change these anytime in Settings → LDView tab
          </p>
        </div>
      ),
      highlight: 'settings'
    },
    {
      title: `You're All Set! 🎉`,
      content: (
        <div className="space-y-4">
          <p className="text-dk-5/90">
            You're ready to start generating 3D-printable LEGO parts!
          </p>
          <div className="p-4 rounded-lg bg-dk-3/50 border border-dk-3">
            <p className="text-sm text-dk-5/90 mb-3">
              <strong>Next steps:</strong>
            </p>
            <ol className="text-sm text-dk-5/80 space-y-2 list-decimal list-inside">
              <li>Search for a LEGO set on the home page</li>
              <li>Create a project from the set details</li>
              <li>Generate STL files from your project</li>
              <li>Download and print!</li>
            </ol>
          </div>
          <button
            onClick={handleComplete}
            className="w-full px-6 py-3 bg-mint text-dk-1 rounded-lg font-medium hover:opacity-90 transition"
          >
            Start Using BrickGen
          </button>
          <p className="text-xs text-dk-5/60 text-center">
            Need help? Check out the Guide page
          </p>
        </div>
      )
    }
  ]

  const currentStepData = steps[currentStep]

  return (
    <>
      {/* Backdrop overlay */}
      <div className="fixed inset-0 bg-black/70 z-40 backdrop-blur-sm" />
      
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

      {/* Wizard card */}
      <div className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-2xl px-4">
        <div className="bg-dk-2 rounded-xl shadow-2xl border border-dk-3 overflow-hidden">
          {/* Header */}
          <div className="bg-dk-3/50 px-6 py-4 border-b border-dk-3">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold text-dk-5">{currentStepData.title}</h2>
              <button
                onClick={handleSkip}
                className="text-dk-5/60 hover:text-dk-5 transition"
                title="Skip onboarding"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            {/* Progress indicator */}
            <div className="flex gap-2 mt-4">
              {steps.map((_, idx) => (
                <div
                  key={idx}
                  className={`h-1 flex-1 rounded-full transition-colors ${
                    idx <= currentStep ? 'bg-mint' : 'bg-dk-3'
                  }`}
                />
              ))}
            </div>
          </div>

          {/* Content */}
          <div className="p-6">
            {currentStepData.content}
          </div>
        </div>
      </div>
    </>
  )
}

export default OnboardingWizard
