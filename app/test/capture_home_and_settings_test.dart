import 'dart:io';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:ecocycle_ai/core/app_state.dart';
import 'package:ecocycle_ai/screens/home_screen.dart';
import 'package:ecocycle_ai/screens/profile_settings_screen.dart';

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

  await tester.pumpAndSettle();

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
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('Capture Home English, Home Hindi, and Profile Settings screenshots', (WidgetTester tester) async {
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final appState = AppState();
    final outDir = 'D:/EcoCycle AI/screenshots';

    // 1. Home Screen (English)
    await _captureWidget(
      tester,
      HomeScreen(appState: appState),
      '$outDir/verify_home_en.png',
    );

    // 2. Switch to Hindi and capture
    await appState.setLanguage('hi');
    await _captureWidget(
      tester,
      HomeScreen(appState: appState),
      '$outDir/verify_home_hi.png',
    );

    // 3. Profile Settings Screen
    await _captureWidget(
      tester,
      ProfileSettingsScreen(appState: appState),
      '$outDir/verify_settings.png',
    );
  });
}

