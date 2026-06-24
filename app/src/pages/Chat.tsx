export default function Chat() {
  return (
    <div className="webview-page">
      <iframe
        src="http://127.0.0.1:8765/"
        title="GBT Chat"
        sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-downloads"
      />
    </div>
  );
}
