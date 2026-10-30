import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ecocycle_ai/core/app_state.dart';
import 'package:ecocycle_ai/screens/ecocredits_screen.dart';
import 'package:ecocycle_ai/screens/my_reports_screen.dart';
import 'package:ecocycle_ai/screens/user_qr_screen.dart';

void main() {
  testWidgets('Screen 12: My Reports renders header, filter chips & empty/report states',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final appState = AppState();
    await tester.pumpWidget(MaterialApp(
      home: MyReportsScreen(appState: appState),
    ));

    expect(find.text('My Reports'), findsOneWidget);
    expect(find.text('Track submitted waste & debris requests'), findsOneWidget);

    // Verify filter choice chips matching approved reference
    expect(find.text('All'), findsOneWidget);
    expect(find.text('In Progress'), findsOneWidget);
    expect(find.text('Completed'), findsOneWidget);

    // Verify EcoPass banner
    expect(find.textContaining('EcoPass ID:'), findsOneWidget);
    expect(find.text('New Report'), findsOneWidget);
  });

  testWidgets('Screen 13: User QR Code renders My QR Code card, QR & Download CTA',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final appState = AppState();
    await tester.pumpWidget(MaterialApp(
      home: UserQRScreen(appState: appState),
    ));

    expect(find.text('My QR Code'), findsOneWidget);
    expect(find.textContaining('Scan to view your profile'), findsOneWidget);
    expect(find.text(appState.activeEcoPassId), findsOneWidget);
    expect(find.text('Download QR'), findsOneWidget);
  });

  testWidgets('Screen 14: EcoCredits & Rewards renders balance, breakdown & rewards catalog',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final appState = AppState();
    await tester.pumpWidget(MaterialApp(
      home: EcoCreditsScreen(appState: appState),
    ));

    expect(find.text('EcoCredits & Rewards'), findsOneWidget);
    expect(find.text('Your EcoCredits'), findsOneWidget);
    expect(find.text('140'), findsOneWidget);

    // Verify Breakdown Pills
    expect(find.textContaining('Earned:'), findsOneWidget);
    expect(find.textContaining('Redeemed:'), findsOneWidget);

    // Verify Rewards Catalog
    expect(find.text('Rewards'), findsOneWidget);
    expect(find.text('Tree Plantation'), findsOneWidget);
    expect(find.text('Eco Voucher'), findsOneWidget);
    expect(find.text('Marketplace Discount'), findsOneWidget);

    // Verify Transaction History Header
    expect(find.text('Transaction History'), findsOneWidget);
  });
}
