import 'dart:io';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ecocycle_ai/core/app_state.dart';
import 'package:ecocycle_ai/screens/login_screen.dart';
import 'package:ecocycle_ai/screens/otp_verification_screen.dart';
import 'package:ecocycle_ai/screens/create_profile_screen.dart';

Future<void> _captureWidget(WidgetTester tester, Widget widget, String outputPath) async {
  tester.view.physicalSize = const Size(1170, 2532);
  tester.view.devicePixelRatio = 3.0;

  final key = GlobalKey();

  await tester.pumpWidget(
    MaterialApp(
      debugShowCheckedModeBanner: false,
      home: RepaintBoundary(
        key: key,
        child: widget,
      ),
    ),
  );

  await tester.pump(const Duration(milliseconds: 100));

  await tester.runAsync(() async {
    final boundary = key.currentContext!.findRenderObject() as RenderRepaintBoundary;
    final image = await boundary.toImage(pixelRatio: 1.0);
    final byteData = await image.toByteData(format: ui.ImageByteFormat.png);
    final pngBytes = byteData!.buffer.asUint8List();

    final file = File(outputPath);
    await file.parent.create(recursive: true);
    await file.writeAsBytes(pngBytes);
  });
}

void main() {
  testWidgets('Generate visual review screenshots for Stage 1', (WidgetTester tester) async {
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final appState = AppState();
    final outDir = 'D:/EcoCycle AI/screenshots';

    // 1. Screen 1: Login
    await _captureWidget(
      tester,
      LoginScreen(appState: appState),
      '$outDir/screen1_login.png',
    );

    // 2. Screen 2: OTP Verification
    await _captureWidget(
      tester,
      OtpVerificationScreen(
        appState: appState,
        phoneNumber: '9876543210',
        sessionId: 'session_demo_review',
        demoOtp: '472961',
        cooldownSeconds: 60,
      ),
      '$outDir/screen2_otp_verification.png',
    );

    // 3. Screen 3: Create Profile
    await _captureWidget(
      tester,
      CreateProfileScreen(
        appState: appState,
        verifiedPhone: '9876543210',
      ),
      '$outDir/screen3_create_profile.png',
    );
  });
}
