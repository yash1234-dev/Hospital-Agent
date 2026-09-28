import { useState } from "react"

import { sendNotification } from "../services/api"


function NotificationButton({
  eventType,
  priority = "NORMAL",
  patientId = null,
  admissionId = null,
  incidentId = null,
  title,
  message,
  sourceAgent,
}) {
  const [showForm, setShowForm] = useState(false)

  const [recipientEmail, setRecipientEmail] = useState("")

  const [sending, setSending] = useState(false)

  const [success, setSuccess] = useState("")

  const [error, setError] = useState("")


  const handleSend = async () => {
    setError("")
    setSuccess("")

    if (!recipientEmail.trim()) {
      setError("Please enter a recipient email address.")
      return
    }

    setSending(true)

    try {
      await sendNotification({
        eventType,
        priority,
        patientId,
        admissionId,
        incidentId,
        title,
        message,
        recipientEmail: recipientEmail.trim(),
        sourceAgent,
      })

      setSuccess("Notification email sent successfully.")

      setRecipientEmail("")
    } catch (err) {
      setError(
        err.message ||
        "Failed to send notification email."
      )
    } finally {
      setSending(false)
    }
  }


  return (
    <div className="mt-5">

      {!showForm && (
        <button
          type="button"
          onClick={() => {
            setShowForm(true)
            setError("")
            setSuccess("")
          }}
          className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 transition"
        >
          ✉ Send Email Notification
        </button>
      )}


      {showForm && (
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">

          <div className="flex items-center justify-between mb-4">

            <div>
              <p className="font-semibold text-slate-800">
                Send Email Notification
              </p>

              <p className="text-xs text-slate-500 mt-1">
                Enter a real test recipient email.
              </p>
            </div>

            <button
              type="button"
              onClick={() => {
                setShowForm(false)
                setError("")
                setSuccess("")
              }}
              className="text-sm text-slate-500 hover:text-slate-800"
            >
              Cancel
            </button>

          </div>


          <label className="block text-sm font-medium text-slate-700 mb-2">
            Recipient Email
          </label>


          <input
            type="email"
            value={recipientEmail}
            onChange={(event) =>
              setRecipientEmail(event.target.value)
            }
            placeholder="friend@gmail.com"
            className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-slate-500"
          />


          <div className="flex items-center gap-3 mt-4">

            <button
              type="button"
              disabled={sending}
              onClick={handleSend}
              className="rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {sending
                ? "Sending..."
                : "Send Notification Email"}
            </button>

          </div>


          {success && (
            <div className="mt-4 rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
              ✓ {success}
            </div>
          )}


          {error && (
            <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

        </div>
      )}

    </div>
  )
}


export default NotificationButton