package br.com.reisos.command;

import android.app.Activity;
import android.app.AlertDialog;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.webkit.CookieManager;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public final class MainActivity extends Activity {
    private WebView webView;
    private LinearLayout statusPanel;
    private TextView statusTitle;
    private TextView statusDetail;
    private Uri commandUri;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        commandUri = Uri.parse(BuildConfig.COMMAND_URL);
        setContentView(buildContent());
        configureWebView();
        loadCommand();
    }

    private View buildContent() {
        FrameLayout root = new FrameLayout(this);
        webView = new WebView(this);
        root.addView(webView, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT));

        statusPanel = new LinearLayout(this);
        statusPanel.setOrientation(LinearLayout.VERTICAL);
        statusPanel.setGravity(Gravity.CENTER);
        statusPanel.setPadding(48, 48, 48, 48);
        statusPanel.setBackgroundColor(Color.rgb(11, 17, 24));

        statusTitle = new TextView(this);
        statusTitle.setTextColor(Color.WHITE);
        statusTitle.setTextSize(20);
        statusTitle.setGravity(Gravity.CENTER);
        statusPanel.addView(statusTitle);

        statusDetail = new TextView(this);
        statusDetail.setTextColor(Color.LTGRAY);
        statusDetail.setTextSize(14);
        statusDetail.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams detailParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        detailParams.setMargins(0, 20, 0, 24);
        statusPanel.addView(statusDetail, detailParams);

        Button retry = new Button(this);
        retry.setText("Tentar novamente");
        retry.setOnClickListener(v -> loadCommand());
        statusPanel.addView(retry);

        root.addView(statusPanel, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT));
        return root;
    }

    private void configureWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setJavaScriptCanOpenWindowsAutomatically(false);
        settings.setSupportMultipleWindows(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);

        CookieManager cookies = CookieManager.getInstance();
        cookies.setAcceptCookie(true);
        cookies.setAcceptThirdPartyCookies(webView, false);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri target = request.getUrl();
                if (sameOrigin(target, commandUri)) {
                    return false;
                }
                if (request.hasGesture() && "https".equalsIgnoreCase(target.getScheme())) {
                    confirmExternalNavigation(target);
                } else {
                    Toast.makeText(MainActivity.this, "Navegação externa bloqueada", Toast.LENGTH_SHORT).show();
                }
                return true;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                if (sameOrigin(Uri.parse(url), commandUri)) {
                    showWebView();
                }
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    showStatus("Command indisponível", "Verifique a rede e tente novamente.");
                }
            }
        });
    }

    private void loadCommand() {
        if (!isSafeConfiguredEndpoint(commandUri)) {
            showStatus(
                    "Endpoint do Command não configurado",
                    "O APK foi construído sem endpoint de produção. Configure COMMAND_URL com HTTPS no build.");
            return;
        }
        showStatus("Conectando ao Command", "Carregando a superfície institucional…");
        webView.loadUrl(commandUri.toString());
    }

    private boolean isSafeConfiguredEndpoint(Uri uri) {
        String host = uri.getHost();
        return "https".equalsIgnoreCase(uri.getScheme())
                && host != null
                && !host.trim().isEmpty()
                && !host.endsWith(".invalid");
    }

    private boolean sameOrigin(Uri left, Uri right) {
        if (left == null || right == null) {
            return false;
        }
        return "https".equalsIgnoreCase(left.getScheme())
                && "https".equalsIgnoreCase(right.getScheme())
                && safeEquals(left.getHost(), right.getHost())
                && effectivePort(left) == effectivePort(right);
    }

    private int effectivePort(Uri uri) {
        return uri.getPort() == -1 ? 443 : uri.getPort();
    }

    private boolean safeEquals(String left, String right) {
        return left != null && right != null && left.equalsIgnoreCase(right);
    }

    private void confirmExternalNavigation(Uri target) {
        new AlertDialog.Builder(this)
                .setTitle("Abrir link externo?")
                .setMessage(target.getHost() == null ? target.toString() : target.getHost())
                .setNegativeButton("Cancelar", null)
                .setPositiveButton("Abrir", (dialog, which) -> {
                    android.content.Intent intent = new android.content.Intent(
                            android.content.Intent.ACTION_VIEW, target);
                    try {
                        startActivity(intent);
                    } catch (android.content.ActivityNotFoundException error) {
                        Toast.makeText(this, "Nenhum navegador disponível", Toast.LENGTH_SHORT).show();
                    }
                })
                .show();
    }

    private void showStatus(String title, String detail) {
        statusTitle.setText(title);
        statusDetail.setText(detail);
        statusPanel.setVisibility(View.VISIBLE);
        webView.setVisibility(View.INVISIBLE);
    }

    private void showWebView() {
        statusPanel.setVisibility(View.GONE);
        webView.setVisibility(View.VISIBLE);
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
            return;
        }
        super.onBackPressed();
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.stopLoading();
            webView.destroy();
        }
        super.onDestroy();
    }
}
